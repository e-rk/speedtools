#
# Copyright (c) 2023 Rafał Kuźnia <rafal.kuznia@protonmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from functools import total_ordering
from itertools import chain, groupby
from math import pi, radians
from pathlib import Path
from typing import Any, Literal

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
    VehicleLightType,
    Vertex,
)
from speedtools.utils import (
    create_pil_image,
    image_to_png,
    make_horizon_texture,
    pil_image_to_png,
)

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

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


@total_ordering
@dataclass(frozen=True)
class ExtendedResource:
    resource: Resource
    backface_culling: bool
    transparent: bool
    highly_reflective: bool
    non_reflective: bool
    animation_ticks: int
    animation_resources: tuple[Resource, ...]
    billboard: bool

    def __lt__(self, other: ExtendedResource) -> bool:
        return hash(self) < hash(other)


class BaseImporter(metaclass=ABCMeta):
    def __init__(
        self, material_map: Callable[[Polygon], Resource], import_shading: bool = False
    ) -> None:
        self.materials: dict[ExtendedResource, bpy.types.Material] = {}
        self.images: dict[Resource, bpy.types.Image] = {}
        self.material_map = material_map
        self.import_shading = import_shading
        self.rot_mat = mathutils.Euler(
            (0.0, 0.0, pi)
        ).to_matrix()  # Transformation from game space to Blender space

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
            return replace(polygon, face=face)

        polygons = unique_vert_polys + [_make_polygon(polygon) for polygon in duplicate_vert_polys]
        vertices = list(mesh.vertices) + verts_to_duplicate
        return replace(mesh, vertices=vertices, polygons=polygons)

    def _extender_resource_map(self, polygon: Polygon) -> ExtendedResource:
        resource = self.material_map(polygon)
        animation_resources = []
        for i in range(polygon.animation_count):
            next_poly = replace(polygon, material=(polygon.material + i))
            animation_resources.append(self.material_map(next_poly))
        return ExtendedResource(
            resource=resource,
            backface_culling=polygon.backface_culling,
            transparent=polygon.transparent,
            highly_reflective=polygon.highly_reflective,
            non_reflective=polygon.non_reflective,
            animation_ticks=polygon.animation_ticks,
            animation_resources=tuple(animation_resources),
            billboard=polygon.billboard,
        )

    def _link_texture_to_shader(
        self,
        node_tree: bpy.types.NodeTree,
        texture: bpy.types.Node,
        shader: bpy.types.Node,
        resource: Resource,
    ) -> None:
        if self.import_shading:
            color_attributes = node_tree.nodes.new("ShaderNodeAttribute")
            color_attributes.attribute_name = "Shading"  # type: ignore[attr-defined]
            mixer = node_tree.nodes.new("ShaderNodeMix")
            mixer.data_type = "RGBA"  # type: ignore[attr-defined]
            mixer.blend_type = "MULTIPLY"  # type: ignore[attr-defined]
            mixer.inputs[0].default_value = 1.0  # type: ignore[attr-defined]
            node_tree.links.new(texture.outputs["Color"], mixer.inputs["A"])
            node_tree.links.new(color_attributes.outputs["Color"], mixer.inputs["B"])
            node_tree.links.new(mixer.outputs["Result"], shader.inputs["Base Color"])
        else:
            node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
        if resource.blend_mode is None:
            math_node = node_tree.nodes.new("ShaderNodeMath")
            math_node.operation = "ROUND"  # type: ignore[attr-defined]
            node_tree.links.new(texture.outputs["Alpha"], math_node.inputs["Value"])
            node_tree.links.new(math_node.outputs["Value"], shader.inputs["Alpha"])
        else:
            node_tree.links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])

    def _set_blend_mode(
        self,
        node_tree: bpy.types.NodeTree,
        shader_output: bpy.types.NodeSocket,
        bpy_material: bpy.types.Material,
        resource: Resource,
    ) -> bpy.types.NodeSocket:
        output_socket = shader_output
        if resource.blend_mode is BlendMode.ADDITIVE:
            bpy_material["SPT_additive"] = True
            transparent_bsdf = node_tree.nodes.new("ShaderNodeBsdfTransparent")
            add_shader = node_tree.nodes.new("ShaderNodeAddShader")
            node_tree.links.new(shader_output, add_shader.inputs[0])
            node_tree.links.new(transparent_bsdf.outputs["BSDF"], add_shader.inputs[1])
            output_socket = add_shader.outputs["Shader"]
        return output_socket

    def _image_to_bpy_image(self, name: str, image: Any) -> bpy.types.Image:
        image_data = pil_image_to_png(image)
        bpy_image = bpy.data.images.new(name, 8, 8)
        bpy_image.pack(data=image_data, data_len=len(image_data))  # type: ignore[arg-type]
        bpy_image.source = "FILE"
        return bpy_image

    def _image_from_resource(self, resource: Resource) -> bpy.types.Image:
        image_data = image_to_png(resource.image)
        bpy_image = bpy.data.images.new(resource.name, 8, 8)
        bpy_image.pack(data=image_data, data_len=len(image_data))  # type: ignore[arg-type]
        bpy_image.source = "FILE"
        return bpy_image

    def _image_from_resource_cached(self, resource: Resource) -> bpy.types.Image:
        try:
            return self.images[resource]
        except KeyError:
            img = self._image_from_resource(resource)
            self.images[resource] = img
        return self.images[resource]

    def _make_material(self, ext_resource: ExtendedResource) -> bpy.types.Material:
        resource = ext_resource.resource
        bpy_material = bpy.data.materials.new(resource.name)
        bpy_material.use_nodes = True
        node_tree = bpy_material.node_tree
        bsdf = node_tree.nodes["Principled BSDF"]  # type: ignore[union-attr]
        bsdf.inputs["Specular IOR Level"].default_value = 0.25  # type: ignore[union-attr]
        bsdf.inputs["Roughness"].default_value = 0.05  # type: ignore[union-attr]
        bsdf.inputs["Metallic"].default_value = 0.0  # type: ignore[union-attr]
        if ext_resource.transparent:
            bsdf.inputs["Alpha"].default_value = 0.04  # type: ignore[union-attr]
            bsdf.inputs["Roughness"].default_value = 0.0  # type: ignore[union-attr]
            bsdf.inputs["Specular IOR Level"].default_value = 0.5  # type: ignore[union-attr]
            bpy_material["SPT_transparent"] = True
        else:
            material_output = node_tree.nodes.get("Material Output")  # type: ignore[union-attr]
            image = self._image_from_resource_cached(resource)
            image_texture = node_tree.nodes.new("ShaderNodeTexImage")  # type: ignore[union-attr]
            image_texture.image = image  # type: ignore[union-attr]
            image_texture.extension = "EXTEND"  # type: ignore[union-attr]
            self._link_texture_to_shader(
                node_tree=node_tree,  # type: ignore[arg-type]
                texture=image_texture,
                shader=bsdf,
                resource=resource,
            )
            output_socket = self._set_blend_mode(
                node_tree=node_tree,  # type: ignore[arg-type]
                shader_output=bsdf.outputs["BSDF"],
                bpy_material=bpy_material,
                resource=resource,
            )
            node_tree.links.new(output_socket, material_output.inputs["Surface"])  # type: ignore[union-attr]
        if ext_resource.highly_reflective:
            # bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)  # type: ignore[union-attr]
            bsdf.inputs["Specular IOR Level"].default_value = 0.50  # type: ignore[union-attr]
        if ext_resource.non_reflective:
            bsdf.inputs["Roughness"].default_value = 1.0  # type: ignore[union-attr]
            bsdf.inputs["Specular IOR Level"].default_value = 0.0  # type: ignore[union-attr]
        bpy_material.use_backface_culling = ext_resource.backface_culling
        if ext_resource.animation_resources:
            bpy_material["SPT_animation_images"] = [
                img.name for img in ext_resource.animation_resources
            ]
            bpy_material["SPT_animation_ticks"] = ext_resource.animation_ticks
        for resource in ext_resource.animation_resources:
            self._image_from_resource(resource)
        bpy_material["SPT_billboard"] = ext_resource.billboard
        return bpy_material

    def _map_material(self, ext_resource: ExtendedResource) -> bpy.types.Material:
        try:
            return self.materials[ext_resource]
        except KeyError:
            bpy_material = self._make_material(ext_resource=ext_resource)
            self.materials[ext_resource] = bpy_material
        return self.materials[ext_resource]

    def make_base_mesh(self, name: str, mesh: BaseMesh) -> bpy.types.Mesh:
        vertices_rot = [mathutils.Vector(vert) @ self.rot_mat for vert in mesh.vertex_locations]
        bpy_mesh = bpy.data.meshes.new(name)
        bpy_mesh.from_pydata(
            vertices=vertices_rot,
            edges=[],
            faces=[polygon.face for polygon in mesh.polygons],
        )
        return bpy_mesh

    def set_object_location(self, obj: bpy.types.Object, location: Vector3d) -> None:
        mu_location = mathutils.Vector(location)
        obj.location = self.rot_mat @ mu_location

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
            rot_quat = mathutils.Euler((0.0, 0.0, pi)).to_quaternion()
            mu_location = rot_quat @ mathutils.Vector(location)
            mu_quaternion = mathutils.Quaternion(quaternion)
            mu_quaternion = mu_quaternion.normalized()
            mu_quaternion = rot_quat @ mu_quaternion.inverted()
            obj.rotation_quaternion = rot_quat
            obj.delta_location = mu_location
            obj.delta_rotation_quaternion = mu_quaternion
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
        transform: Matrix3x3 | mathutils.Matrix,
        offset: mathutils.Euler | None = None,
    ) -> None:
        mu_matrix = self.rot_mat @ mathutils.Matrix(transform)  # type: ignore[arg-type]
        if offset:
            mu_euler = offset
            mu_euler.rotate(mu_matrix.to_euler("XYZ"))  # pylint: disable=all
        else:
            mu_euler = mu_matrix.to_euler("XYZ")  # pylint: disable=all
        obj.rotation_mode = "XYZ"
        obj.rotation_euler = mu_euler

    def make_drawable_object(self, name: str, mesh: DrawableMesh) -> bpy.types.Object:
        bpy_mesh = self.make_base_mesh(name=name, mesh=mesh)
        uv_layer = bpy_mesh.uv_layers.new()
        uvs = collapse(polygon.uv for polygon in mesh.polygons)
        uv_layer.data.foreach_set("uv", list(uvs))
        if mesh.vertex_normals:
            normals = [mathutils.Vector(normal) @ self.rot_mat for normal in mesh.vertex_normals]
            bpy_mesh.normals_split_custom_set_from_vertices(normals)  # type: ignore[arg-type]
        if mesh.vertex_colors and self.import_shading:
            colors = collapse(color.rgba_float for color in mesh.vertex_colors)
            bpy_colors = bpy_mesh.color_attributes.new(
                name="Shading", type="BYTE_COLOR", domain="POINT"
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
                if not mesh.vertex_normals:
                    bpy_polygon.use_smooth = True
                bpy_polygon.material_index = index
        bpy_mesh.validate()
        bpy_obj = bpy.data.objects.new(name, bpy_mesh)
        if mesh.shape_keys:
            bpy_obj.shape_key_add(name="Basis")
        return bpy_obj

    def make_base_light(
        self,
        name: str,
        light: Light,
        light_type: Literal["POINT", "SUN", "SPOT", "AREA"] | None = "POINT",
        energy: int = 500,
        cutoff_distance: float = 15.0,
    ) -> bpy.types.Light:
        bpy_light = bpy.data.lights.new(name=name, type=light_type)
        bpy_light.color = light.color.rgb_float
        bpy_light.use_custom_distance = True
        bpy_light.cutoff_distance = cutoff_distance
        bpy_light.specular_factor = 0.2
        bpy_light.energy = energy  # type: ignore[attr-defined]
        bpy_light.use_shadow = False
        return bpy_light

    def make_point_light_object(self, name: str, light: Light) -> bpy.types.Object:
        bpy_light = self.make_base_light(name=name, light=light, light_type="POINT")
        bpy_obj = bpy.data.objects.new(name=name, object_data=bpy_light)
        self.set_object_location(obj=bpy_obj, location=light.location)
        return bpy_obj

    def make_spot_light_object(
        self, name: str, light: Light, energy: int, angle: float, cutoff_distance: float
    ) -> bpy.types.Object:
        bpy_light = self.make_base_light(
            name=name,
            light=light,
            energy=energy,
            light_type="SPOT",
            cutoff_distance=cutoff_distance,
        )
        bpy_light.spot_size = angle  # type: ignore[attr-defined]
        bpy_light.spot_blend = 0.5  # type: ignore[attr-defined]
        bpy_obj = bpy.data.objects.new(name=name, object_data=bpy_light)
        self.set_object_location(obj=bpy_obj, location=light.location)
        return bpy_obj

    def make_directional_light_object(
        self, name: str, light: DirectionalLight
    ) -> bpy.types.Object:
        bpy_sun = bpy.data.lights.new(name=name, type="SUN")
        bpy_obj = bpy.data.objects.new(name=name, object_data=bpy_sun)
        mu_rot = self.rot_mat @ mathutils.Euler(light.euler_xyz).to_matrix()
        bpy_obj.rotation_mode = "XYZ"
        bpy_obj.rotation_euler = mu_rot.to_euler()
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
            mu_vector = self.rot_mat @ mathutils.Vector(vertex.location)
            data.co = mu_vector  # type: ignore[attr-defined]


class TrackImportStrategy(metaclass=ABCMeta):
    @abstractmethod
    def import_track(
        self,
        track: TrackData,
        import_collision: bool = False,
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
            bpy_obj = self.make_drawable_object(name=name, mesh=mesh)
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
            bpy_obj = self.make_drawable_object(name=name, mesh=mesh)
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
            bpy_obj = self.make_point_light_object(name=name, light=light)
            light_collection.objects.link(bpy_obj)
        directional_light = track.directional_light
        if directional_light:
            sun = directional_light.resource
            sun_image = create_pil_image(sun.image)
            bpy_sun = self._image_to_bpy_image("sun", sun_image)
            bpy_obj = self.make_directional_light_object(name="sun", light=directional_light)
            bpy_obj["SPT_sun"] = {
                "additive": directional_light.additive,
                "is_front": directional_light.in_front,
                "rotates": directional_light.rotates,
                "radius": directional_light.radius,
            }
            light_collection.objects.link(bpy_obj)
        if import_cameras:
            camera_collection = bpy.data.collections.new("Cameras")
            bpy.context.scene.collection.children.link(camera_collection)
            for index, camera in enumerate(track.cameras):
                bpy_obj = self.make_camera_object(name=f"Camera {index}", camera=camera)
                camera_collection.objects.link(bpy_obj)
        spt_track = {}
        gltf_transform = mathutils.Euler((-pi / 2.0, 0.0, 0.0)).to_matrix() @ self.rot_mat
        waypoints = chain.from_iterable(segment.waypoints for segment in track.track_segments)
        waypoint_metadata = [gltf_transform @ mathutils.Vector(w) for w in waypoints]
        spt_track["waypoints"] = [(w.x, w.y, w.z) for w in waypoint_metadata]
        if import_ambient:

            def color_to_dict(color: Color) -> dict[str, float]:
                red, green, blue = color.rgb_float
                return {"red": red, "green": green, "blue": blue}

            environment = {}
            ambient_color = track.ambient_color
            environment["ambient"] = color_to_dict(ambient_color)
            horizon = track.horizon
            environment["horizon"] = {
                "sun_side": color_to_dict(horizon.sun_side),  # type: ignore[dict-item]
                "sun_top": color_to_dict(horizon.sun_top_side),  # type: ignore[dict-item]
                "sun_opposite": color_to_dict(horizon.sun_opposite_side),  # type: ignore[dict-item]
                "earth_bottom": color_to_dict(horizon.earth_bottom),  # type: ignore[dict-item]
                "earth_top": color_to_dict(horizon.earth_top),  # type: ignore[dict-item]
            }
            spt_track["environment"] = environment  # type: ignore[assignment]
        bpy.context.scene["SPT_track"] = spt_track
        sky_images = list(track.sky_images)
        if sky_images:
            horizon_image = make_horizon_texture(sky_images)
            bpy_image = self._image_to_bpy_image("horizon", horizon_image)
        clouds = track.clouds
        clouds_image = create_pil_image(clouds.image)
        bpy_clouds = self._image_to_bpy_image("clouds", clouds_image)


class CarImporterSimple(BaseImporter):
    car_light_attributes = {  # (Energy, angle, cutoff, rotation)
        VehicleLightType.HEADLIGHT: (
            200,
            90,
            100.0,
            mathutils.Matrix.Rotation(radians(90), 3, "X"),
        ),
        VehicleLightType.DIRECTIONAL: (
            20,
            160,
            1.0,
            mathutils.Matrix.Rotation(radians(-90), 3, "X"),
        ),
        VehicleLightType.BRAKELIGHT: (
            20,
            160,
            1.0,
            mathutils.Matrix.Rotation(radians(-90), 3, "X"),
        ),
        VehicleLightType.REVERSE: (20, 160, 1.0, mathutils.Matrix.Rotation(radians(-90), 3, "X")),
        VehicleLightType.TAILLIGHT: (
            10,
            160,
            1.0,
            mathutils.Matrix.Rotation(radians(-90), 3, "X"),
        ),
        VehicleLightType.SIREN: (100, 180, 40.0, mathutils.Matrix.Rotation(radians(-90), 3, "X")),
    }

    def import_car(self, car: VivData, import_interior: bool, import_lights: bool) -> None:
        car_collection = bpy.data.collections.new("Car parts")
        bpy.context.scene.collection.children.link(car_collection)
        parts = car.interior if import_interior else car.parts
        for part in parts:
            bpy_obj = self.make_drawable_object(name=part.name, mesh=part.mesh)
            self.set_object_location(obj=bpy_obj, location=part.location)
            car_collection.objects.link(bpy_obj)
            for shape_key in part.mesh.shape_keys:
                self.make_shape_key(obj=bpy_obj, shape_key=shape_key)
        light_collection = bpy.data.collections.new("Car lights")
        bpy.context.scene.collection.children.link(light_collection)
        if import_lights:
            for index, light in enumerate(car.lights):
                name = f"{light.type.name.lower()}-{index}"
                attributes = self.car_light_attributes[light.type]
                bpy_obj = self.make_spot_light_object(
                    name=name,
                    light=light,
                    energy=attributes[0],
                    angle=radians(attributes[1]),
                    cutoff_distance=attributes[2],
                )
                self.set_object_rotation(obj=bpy_obj, transform=attributes[3])
                light_collection.objects.link(bpy_obj)
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

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> set[Literal["RUNNING_MODAL", "CANCELLED", "FINISHED", "PASS_THROUGH", "INTERFACE"]]:
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(
        self, context: bpy.types.Context
    ) -> set[Literal["RUNNING_MODAL", "CANCELLED", "FINISHED", "PASS_THROUGH", "INTERFACE"]]:
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
        import_strategy: TrackImportStrategy
        import_strategy = TrackImportGLTF(
            material_map=track.get_polygon_material, import_shading=self.import_shading
        )
        import_strategy.import_track(
            track=track,
            import_collision=self.import_collision,
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

    import_lights: BoolProperty(  # type: ignore[valid-type]
        name="Import car lights",
        description="Import car lights and assign default attribute values",
        default=False,
    )

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> set[Literal["RUNNING_MODAL", "CANCELLED", "FINISHED", "PASS_THROUGH", "INTERFACE"]]:
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(
        self, context: bpy.types.Context
    ) -> set[Literal["RUNNING_MODAL", "CANCELLED", "FINISHED", "PASS_THROUGH", "INTERFACE"]]:
        car = VivData.from_file(Path(self.directory, "CAR.VIV"))
        logger.debug(car)

        if self.import_interior:
            resource = one(car.interior_materials)
        else:
            resource = one(car.body_materials)
        importer = CarImporterSimple(material_map=lambda _: resource)
        importer.import_car(
            car, import_interior=self.import_interior, import_lights=self.import_lights
        )

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
