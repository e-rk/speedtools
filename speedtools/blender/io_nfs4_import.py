#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import total_ordering
from itertools import chain, groupby
from math import pi
from pathlib import Path
from typing import Any

import bpy
import mathutils
from bpy.props import BoolProperty, EnumProperty, StringProperty
from more_itertools import collapse, duplicates_everseen, one, unique_everseen

from speedtools import TrackData, VivData
from speedtools.types import (
    Action,
    AnimationAction,
    BaseMesh,
    BlendMode,
    Camera,
    Color,
    DirectionalLight,
    DrawableMesh,
    Light,
    Matrix3x3,
    Part,
    Polygon,
    Resource,
    ShapeKey,
    Vector3d,
    Vertex,
)
from speedtools.utils import image_to_png

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

major_version, _, _ = bpy.app.version  # type: ignore[misc]


bl_info = {
    "name": "Import NFS4 Track",
    "author": "Rafał Kuźnia",
    "version": (1, 0, 0),
    "blender": (3, 4, 1),
    "location": "File > Import > Track resource",
    "description": "Imports a NFS4 track files (meshes, textures and objects)."
    "Scripts/Import-Export/Track_Resource",
    "category": "Import-Export",
}


@total_ordering
@dataclass(frozen=True)
class ExtendedResource:
    resource: Resource
    backface_culling: bool

    def __lt__(self, other: ExtendedResource) -> bool:
        return hash(self) < hash(other)


class BaseImporter(metaclass=ABCMeta):
    def __init__(self, material_map: Callable[[Polygon], Resource]) -> None:
        self.materials: dict[ExtendedResource, bpy.types.Material] = {}
        self.material_map = material_map

    @classmethod
    def duplicate_common_vertices(cls, mesh: DrawableMesh) -> DrawableMesh:
        unique_vert_polys = list(unique_everseen(mesh.polygons, key=lambda x: frozenset(x.face)))
        duplicate_vert_polys = list(
            duplicates_everseen(mesh.polygons, key=lambda x: frozenset(x.face))
        )
        faces = frozenset(chain.from_iterable(poly.face for poly in duplicate_vert_polys))
        verts_to_duplicate = [mesh.vertices[x] for x in faces]
        mapping = {f: i for i, f in enumerate(faces, start=len(mesh.vertices))}

        def _make_polygon(polygon: Polygon) -> Polygon:
            face = tuple(mapping[f] for f in polygon.face)
            return Polygon(
                face=face,
                uv=polygon.uv,
                material=polygon.material,
                backface_culling=polygon.backface_culling,
            )

        polygons = unique_vert_polys + [_make_polygon(polygon) for polygon in duplicate_vert_polys]
        vertices = list(mesh.vertices) + verts_to_duplicate
        return DrawableMesh(vertices=vertices, polygons=polygons)

    def _extender_resource_map(self, polygon: Polygon) -> ExtendedResource:
        resource = self.material_map(polygon)
        return ExtendedResource(resource=resource, backface_culling=polygon.backface_culling)

    def _link_texture_to_shader(
        self, node_tree: bpy.types.NodeTree, texture: bpy.types.Node, shader: bpy.types.Node
    ) -> None:
        node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
        node_tree.links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])

    def _set_blend_mode(
        self,
        node_tree: bpy.types.NodeTree,
        shader_output: bpy.types.NodeSocket,
        bpy_material: bpy.types.Material,
        resource: Resource,
    ) -> bpy.types.NodeSocket:
        if resource.blend_mode is BlendMode.ALPHA:
            bpy_material.blend_method = "BLEND"
        elif resource.blend_mode is BlendMode.ADDITIVE:
            bpy_material["SPT_additive"] = True
        else:
            bpy_material.alpha_threshold = 0.001
            bpy_material.blend_method = "CLIP"
        return shader_output

    def _image_from_resource(self, resource: Resource) -> bpy.types.Image:
        image_data = image_to_png(resource.image)
        bpy_image = bpy.data.images.new(resource.name, 8, 8)
        bpy_image.pack(data=image_data, data_len=len(image_data))
        bpy_image.source = "FILE"
        return bpy_image

    def _make_material(self, ext_resource: ExtendedResource) -> bpy.types.Material:
        resource = ext_resource.resource
        bpy_material = bpy.data.materials.new(resource.name)
        bpy_material.use_nodes = True
        image = self._image_from_resource(resource)
        node_tree = bpy_material.node_tree
        material_output = node_tree.nodes.get("Material Output")
        image_texture = node_tree.nodes.new("ShaderNodeTexImage")
        image_texture.image = image  # type: ignore[attr-defined]
        image_texture.extension = "EXTEND"  # type: ignore[attr-defined]
        bsdf = node_tree.nodes["Principled BSDF"]
        if major_version == 3:  # type: ignore[has-type]
            bsdf.inputs["Specular"].default_value = 0  # type: ignore[attr-defined]
            bsdf.inputs["Sheen Tint"].default_value = 0  # type: ignore[attr-defined]
        else:
            # IOR Level
            bsdf.inputs[12].default_value = 0  # type: ignore[attr-defined]
        bsdf.inputs["Roughness"].default_value = 1  # type: ignore[attr-defined]
        self._link_texture_to_shader(node_tree=node_tree, texture=image_texture, shader=bsdf)
        output_socket = self._set_blend_mode(
            node_tree=node_tree,
            shader_output=bsdf.outputs["BSDF"],
            bpy_material=bpy_material,
            resource=resource,
        )
        node_tree.links.new(output_socket, material_output.inputs["Surface"])
        bpy_material.use_backface_culling = ext_resource.backface_culling
        return bpy_material

    def _map_material(self, ext_resource: ExtendedResource) -> bpy.types.Material:
        try:
            return self.materials[ext_resource]
        except KeyError:
            bpy_material = self._make_material(ext_resource=ext_resource)
            self.materials[ext_resource] = bpy_material
        return self.materials[ext_resource]

    def make_base_mesh(self, name: str, mesh: BaseMesh) -> bpy.types.Mesh:
        bpy_mesh = bpy.data.meshes.new(name)
        bpy_mesh.from_pydata(
            vertices=list(mesh.vertex_locations),
            edges=[],
            faces=[polygon.face for polygon in mesh.polygons],
        )
        return bpy_mesh

    def set_object_location(self, obj: bpy.types.Object, location: Vector3d) -> None:
        mu_location = mathutils.Vector(location)
        obj.location = mu_location  # type: ignore[assignment]

    def set_object_action(self, obj: bpy.types.Object, action: AnimationAction) -> None:
        animation = action.animation
        obj.rotation_mode = "QUATERNION"
        if obj.animation_data is None:
            anim_data = obj.animation_data_create()
        else:
            anim_data = obj.animation_data
        bpy_action = bpy.data.actions.new(name=str(action.action))
        anim_data.action = bpy_action
        for index, (location, quaternion) in enumerate(
            zip(animation.locations, animation.quaternions)
        ):
            mu_location = mathutils.Vector(location)
            mu_quaternion = mathutils.Quaternion(quaternion)
            mu_quaternion = mu_quaternion.normalized()
            mu_quaternion = mu_quaternion.inverted()
            obj.delta_location = mu_location  # type: ignore[assignment]
            obj.delta_rotation_quaternion = mu_quaternion  # type: ignore[assignment]
            interval = index * animation.delay
            obj.keyframe_insert(
                data_path="delta_location", frame=interval, options={"INSERTKEY_CYCLE_AWARE"}
            )
            obj.keyframe_insert(
                data_path="delta_rotation_quaternion",
                frame=interval,
                options={"INSERTKEY_CYCLE_AWARE"},
            )
        points = chain.from_iterable(fcurve.keyframe_points for fcurve in bpy_action.fcurves)
        for point in points:
            point.interpolation = "LINEAR"
        bpy_action.name = f"{obj.name}-action-{action.action}"
        track = anim_data.nla_tracks.new()
        track.strips.new(name=bpy_action.name, start=0, action=bpy_action)

    def set_object_rotation(
        self,
        obj: bpy.types.Object,
        transform: Matrix3x3,
        offset: mathutils.Euler | None = None,
    ) -> None:
        mu_matrix = mathutils.Matrix(transform)
        if offset:
            mu_euler = offset
            mu_euler.rotate(mu_matrix.to_euler("XYZ"))  # type: ignore # pylint: disable=all
        else:
            mu_euler = mu_matrix.to_euler("XYZ")  # type: ignore # pylint: disable=all
        obj.rotation_mode = "XYZ"
        obj.rotation_euler = mu_euler  # type: ignore[assignment]

    def make_drawable_object(
        self, name: str, mesh: DrawableMesh, import_shading: bool = False
    ) -> bpy.types.Object:
        bpy_mesh = self.make_base_mesh(name=name, mesh=mesh)
        uv_layer = bpy_mesh.uv_layers.new()
        uvs = collapse(polygon.uv for polygon in mesh.polygons)
        uv_layer.data.foreach_set("uv", list(uvs))
        if mesh.vertex_normals:
            normals = tuple(mesh.vertex_normals)
            # I have no idea if setting the normals even works
            bpy_mesh.normals_split_custom_set_from_vertices(normals)  # type: ignore[arg-type]
        if mesh.vertex_colors and import_shading:
            colors = collapse(color.rgba_float for color in mesh.vertex_colors)
            bpy_colors = bpy_mesh.color_attributes.new(
                name="Shading", type="FLOAT_COLOR", domain="POINT"
            )
            bpy_colors.data.foreach_set("color", tuple(colors))  # type: ignore[attr-defined]
        polygon_pairs = zip(mesh.polygons, bpy_mesh.polygons)
        sorted_by_material = sorted(polygon_pairs, key=lambda x: self._extender_resource_map(x[0]))
        grouped_by_material = groupby(
            sorted_by_material, key=lambda x: self._extender_resource_map(x[0])
        )
        for index, (key, group) in enumerate(grouped_by_material):
            material = self._map_material(key)
            bpy_mesh.materials.append(material)
            for _, bpy_polygon in group:
                bpy_polygon.use_smooth = True
                bpy_polygon.material_index = index
        bpy_mesh.validate()
        bpy_obj = bpy.data.objects.new(name, bpy_mesh)
        if mesh.shape_keys:
            bpy_obj.shape_key_add(name="Basis")
        return bpy_obj

    def make_light_object(self, name: str, light: Light) -> bpy.types.Object:
        bpy_light = bpy.data.lights.new(name=name, type="POINT")
        bpy_light.color = light.attributes.color.rgb_float  # type: ignore[assignment]
        bpy_light.use_custom_distance = True
        bpy_light.cutoff_distance = 15.0
        bpy_light.specular_factor = 0.2
        bpy_light.energy = 500  # type: ignore[attr-defined]
        bpy_light.use_shadow = False  # type: ignore[attr-defined]
        bpy_obj = bpy.data.objects.new(name=name, object_data=bpy_light)
        self.set_object_location(obj=bpy_obj, location=light.location)
        return bpy_obj

    def make_directional_light_object(
        self, name: str, light: DirectionalLight
    ) -> bpy.types.Object:
        bpy_sun = bpy.data.lights.new(name=name, type="SUN")
        bpy_obj = bpy.data.objects.new(name=name, object_data=bpy_sun)
        mu_euler = mathutils.Euler(light.euler_xyz)
        bpy_obj.rotation_mode = "XYZ"
        bpy_obj.rotation_euler = mu_euler  # type: ignore[assignment]
        return bpy_obj

    def make_camera_object(self, name: str, camera: Camera) -> bpy.types.Object:
        bpy_camera = bpy.data.cameras.new(name=name)
        bpy_obj = bpy.data.objects.new(name=name, object_data=bpy_camera)
        offset = mathutils.Euler((pi / 2, 0, 0))
        self.set_object_location(obj=bpy_obj, location=camera.location)
        self.set_object_rotation(obj=bpy_obj, transform=camera.transform, offset=offset)
        return bpy_obj

    def make_shape_key(self, obj: bpy.types.Object, shape_key: ShapeKey) -> None:
        bpy_shape_key = obj.shape_key_add(name=shape_key.type.name)
        bpy_shape_key.interpolation = "KEY_LINEAR"
        for data, vertex in zip(bpy_shape_key.data, shape_key.vertices, strict=True):
            data.co = vertex.location  # type: ignore[attr-defined]


class TrackImportStrategy(metaclass=ABCMeta):
    @abstractmethod
    def import_track(
        self,
        track: TrackData,
        import_collision: bool = False,
        import_shading: bool = False,
        import_actions: bool = False,
        import_cameras: bool = False,
        import_ambient: bool = False,
    ) -> None:
        pass


class TrackImportGLTF(TrackImportStrategy, BaseImporter):
    def import_track(
        self,
        track: TrackData,
        import_collision: bool = False,
        import_shading: bool = False,
        import_actions: bool = False,
        import_cameras: bool = False,
        import_ambient: bool = False,
    ) -> None:
        bpy.context.scene.render.fps = track.ANIMATION_FPS
        track_collection = bpy.data.collections.new("Track segments")
        bpy.context.scene.collection.children.link(track_collection)
        for index, segment in enumerate(track.track_segments):
            name = f"Segment {index}"
            segment_collection = bpy.data.collections.new(name=name)
            track_collection.children.link(segment_collection)
            mesh = self.duplicate_common_vertices(mesh=segment.mesh)
            bpy_obj = self.make_drawable_object(
                name=name, mesh=mesh, import_shading=import_shading
            )
            segment_collection.objects.link(bpy_obj)
            if import_collision:
                for collision_index, collision_mesh in enumerate(segment.collision_meshes):
                    effect = collision_mesh.collision_effect
                    name = f"Collision {collision_index}.{effect}-colonly"
                    bpy_mesh = self.make_base_mesh(name=name, mesh=collision_mesh)
                    bpy_obj = bpy.data.objects.new(name, bpy_mesh)
                    segment_collection.objects.link(bpy_obj)
                    bpy_obj.hide_set(True)
                    bpy_obj["SPT_surface_type"] = effect.value
        object_collection = bpy.data.collections.new("Objects")
        bpy.context.scene.collection.children.link(object_collection)
        for index, obj in enumerate(track.objects):
            name = f"Object {index}"
            mesh = self.duplicate_common_vertices(mesh=obj.mesh)
            bpy_obj = self.make_drawable_object(
                name=name, mesh=mesh, import_shading=import_shading
            )
            actions = (
                obj.actions
                if import_actions
                else filter(lambda x: x.action is Action.DEFAULT_LOOP, obj.actions)
            )
            for action in actions:
                self.set_object_action(obj=bpy_obj, action=action)
            if obj.location:
                self.set_object_location(obj=bpy_obj, location=obj.location)
            if obj.transform:
                self.set_object_rotation(obj=bpy_obj, transform=obj.transform)
            object_collection.objects.link(bpy_obj)
        light_collection = bpy.data.collections.new("Lights")
        bpy.context.scene.collection.children.link(light_collection)
        for index, light in enumerate(track.lights):
            name = f"Light {index}"
            bpy_obj = self.make_light_object(name=name, light=light)
            light_collection.objects.link(bpy_obj)
        directional_light = track.directional_light
        if directional_light:
            bpy_obj = self.make_directional_light_object(name="sun", light=directional_light)
            light_collection.objects.link(bpy_obj)
        if import_cameras:
            camera_collection = bpy.data.collections.new("Cameras")
            bpy.context.scene.collection.children.link(camera_collection)
            for index, camera in enumerate(track.cameras):
                bpy_obj = self.make_camera_object(name=f"Camera {index}", camera=camera)
                camera_collection.objects.link(bpy_obj)
        spt_track = {}
        waypoints = chain.from_iterable(segment.waypoints for segment in track.track_segments)
        waypoint_metadata = [(w.x, w.y, w.z) for w in waypoints]
        spt_track["waypoints"] = waypoint_metadata
        if import_ambient:

            def color_to_dict(color: Color) -> dict[str, float]:
                red, green, blue = color.rgb_float
                return {"red": red, "green": green, "blue": blue}

            environment = {}
            ambient_color = track.ambient_color
            environment["ambient"] = color_to_dict(ambient_color)
            horizon = track.horizon
            environment["horizon"] = {
                "sun": color_to_dict(horizon.sun_side),  # type: ignore[dict-item]
                "top": color_to_dict(horizon.top_side),  # type: ignore[dict-item]
                "opposite": color_to_dict(horizon.opposite_side),  # type: ignore[dict-item]
            }
            spt_track["environment"] = environment  # type: ignore[assignment]
        bpy.context.scene["SPT_track"] = spt_track


class TrackImportBlender(TrackImportGLTF):
    def _link_texture_to_shader(
        self, node_tree: bpy.types.NodeTree, texture: bpy.types.Node, shader: bpy.types.Node
    ) -> None:
        color_attributes = node_tree.nodes.new("ShaderNodeAttribute")
        color_attributes.attribute_name = "Shading"  # type: ignore[attr-defined]
        mixer = node_tree.nodes.new("ShaderNodeMixRGB")
        mixer.blend_type = "MULTIPLY"  # type: ignore[attr-defined]
        mixer.inputs["Fac"].default_value = 1.0  # type: ignore[attr-defined]
        node_tree.links.new(texture.outputs["Color"], mixer.inputs["Color1"])
        node_tree.links.new(color_attributes.outputs["Color"], mixer.inputs["Color2"])
        node_tree.links.new(mixer.outputs["Color"], shader.inputs["Base Color"])
        node_tree.links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])

    def _set_blend_mode(
        self,
        node_tree: bpy.types.NodeTree,
        shader_output: bpy.types.NodeSocket,
        bpy_material: bpy.types.Material,
        resource: Resource,
    ) -> bpy.types.NodeSocket:
        shader_output = super()._set_blend_mode(
            node_tree=node_tree,
            shader_output=shader_output,
            bpy_material=bpy_material,
            resource=resource,
        )
        output_socket = shader_output
        if resource.blend_mode is BlendMode.ADDITIVE:
            bpy_material.blend_method = "BLEND"
            transparent_bsdf = node_tree.nodes.new("ShaderNodeBsdfTransparent")
            add_shader = node_tree.nodes.new("ShaderNodeAddShader")
            node_tree.links.new(shader_output, add_shader.inputs[0])
            node_tree.links.new(transparent_bsdf.outputs["BSDF"], add_shader.inputs[1])
            output_socket = add_shader.outputs["Shader"]
        return output_socket


class CarImporterSimple(BaseImporter):
    def import_car(self, car: VivData) -> None:
        car_collection = bpy.data.collections.new("Car parts")
        bpy.context.scene.collection.children.link(car_collection)
        for part in car.parts:
            bpy_obj = self.make_drawable_object(name=part.name, mesh=part.mesh)
            self.set_object_location(obj=bpy_obj, location=part.location)
            car_collection.objects.link(bpy_obj)
            for shape_key in part.mesh.shape_keys:
                self.make_shape_key(obj=bpy_obj, shape_key=shape_key)
        dimensions = car.dimensions
        car_metadata = {
            "performance": car.performance,
            "dimensions": (dimensions.x, dimensions.y, dimensions.z),
        }
        bpy.context.scene["SPT_car"] = car_metadata


class TrackImporter(bpy.types.Operator):
    """Import NFS4 Track Operator"""

    bl_idname = "import_scene.nfs4trk"
    bl_label = "Import NFS4 Track"
    bl_description = "Import NFS4 track files"
    bl_options = {"REGISTER", "UNDO"}

    bpy.types.Scene.nfs4trk = None  # type: ignore[attr-defined]

    directory: StringProperty(  # type: ignore[valid-type]
        name="Directory Path",
        description="Directory containing the track files",
        maxlen=1024,
        default="",
    )
    mode: EnumProperty(  # type: ignore[valid-type]
        name="Mode",
        items=(
            (
                "GLTF",
                "GLTF target",
                "Parametrized import of visible track geometry, lights, animations, "
                "collision geometry and more. Stores data that can't be represented in "
                "GLTF 'extras' fields.",
            ),
            (
                "BLENDER",
                "Blender target",
                "This option should be used when accurate look in Blender is desired. "
                "Some data, such as vertex shading, can't be viewed in Blender without specific "
                "shader node connections. Such connections are on the other hand poorly understood "
                "by exporters, such as the GLTF exporter. Therefore this mode must never be "
                "used if you intent to export the track to GLTF. Vertex shading is always enabled "
                "in this mode.",
            ),
        ),
        description="Select importer mode",
    )
    night: BoolProperty(  # type: ignore[valid-type]
        name="Night on", description="Import night track variant", default=False
    )
    weather: BoolProperty(  # type: ignore[valid-type]
        name="Weather on", description="Import rainy track variant", default=False
    )
    mirrored: BoolProperty(  # type: ignore[valid-type]
        name="Mirrored on", description="Import mirrored track variant", default=False
    )
    import_shading: BoolProperty(  # type: ignore[valid-type]
        name="Import vertex shading",
        description="Import original vertex shading to obtain the 'original' track look",
        default=False,
    )
    import_collision: BoolProperty(  # type: ignore[valid-type]
        name="Import collision (experimental)",
        description="Import collision meshes (ending with -colonly)",
        default=False,
    )
    import_actions: BoolProperty(  # type: ignore[valid-type]
        name="Import animation actions (experimental)",
        description="Import track animation actions from CAN files, such as object destruction animation",
        default=False,
    )
    import_cameras: BoolProperty(  # type: ignore[valid-type]
        name="Import cameras (experimental)",
        description="Import track-specific replay cameras",
        default=False,
    )
    import_ambient: BoolProperty(  # type: ignore[valid-type]
        name="Import ambient",
        description="Import ambient light",
        default=False,
    )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[int] | set[str]:
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context) -> set[int] | set[str]:
        directory = Path(self.directory)
        # This should get us from track directory to game root directory
        game_root = directory.parent.parent.parent
        track = TrackData(
            directory=Path(self.directory),
            game_root=game_root,
            mirrored=self.mirrored,
            night=self.night,
            weather=self.weather,
        )
        import_shading = self.import_shading
        import_strategy: TrackImportStrategy
        if self.mode == "GLTF":
            import_strategy = TrackImportGLTF(material_map=track.get_polygon_material)
        elif self.mode == "BLENDER":
            import_strategy = TrackImportBlender(material_map=track.get_polygon_material)
            import_shading = True
        else:
            return {"CANCELLED"}
        import_strategy.import_track(
            track=track,
            import_collision=self.import_collision,
            import_shading=import_shading,
            import_actions=self.import_actions,
            import_cameras=self.import_cameras,
            import_ambient=self.import_ambient,
        )
        return {"FINISHED"}


class CarImporter(bpy.types.Operator):
    """Import NFS4 Car Operator"""

    bl_idname = "import_scene.nfs4car"
    bl_label = "Import NFS4 Car"
    bl_description = "Import NFS4 Car files"
    bl_options = {"REGISTER", "UNDO"}

    bpy.types.Scene.nfs4car = None  # type: ignore

    directory: StringProperty(  # type: ignore
        name="Directory Path",
        description="Directory containing the car files",
        maxlen=1024,
        default="",
    )
    import_interior: BoolProperty(  # type: ignore[valid-type]
        name="Import interior", description="Import car interior geometry", default=False
    )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[int] | set[str]:
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context) -> set[int] | set[str]:
        car = VivData.from_file(Path(self.directory, "CAR.VIV"))
        logger.debug(car)

        if self.import_interior:
            resource = one(car.interior_materials)
            parts = car.interior
        else:
            resource = one(car.body_materials)
            parts = car.parts
        importer = CarImporterSimple(material_map=lambda _: resource)
        importer.import_car(car)

        return {"FINISHED"}


def menu_func(self: Any, context: bpy.types.Context) -> None:
    self.layout.operator(TrackImporter.bl_idname, text="Track resources")
    self.layout.operator(CarImporter.bl_idname, text="Car resources")


def register() -> None:
    bpy.utils.register_class(TrackImporter)
    bpy.utils.register_class(CarImporter)
    bpy.types.TOPBAR_MT_file_import.append(menu_func)


def unregister() -> None:
    bpy.utils.unregister_class(TrackImporter)
    bpy.utils.unregister_class(CarImporter)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func)


if __name__ == "__main__":
    register()
