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
from itertools import groupby
from pathlib import Path
from typing import Any

import bpy
import mathutils
from bpy.props import BoolProperty, EnumProperty, StringProperty
from more_itertools import collapse

from speedtools import TrackData, VivData
from speedtools.types import (
    Animation,
    BaseMesh,
    DrawableMesh,
    Light,
    Part,
    Polygon,
    Resource,
    Vector3d,
)
from speedtools.utils import export_resource

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


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

    def _extender_resource_map(self, polygon: Polygon) -> ExtendedResource:
        resource = self.material_map(polygon)
        return ExtendedResource(resource=resource, backface_culling=polygon.backface_culling)

    def _make_material(self, ext_resource: ExtendedResource) -> bpy.types.Material:
        resource = ext_resource.resource
        images_dir = Path(bpy.path.abspath("//images"))
        export_resource(resource, directory=images_dir)
        bpy_material = bpy.data.materials.new(resource.name)
        bpy_material.use_nodes = True
        image_path = Path(images_dir, f"{resource.name}.png")
        image = bpy.data.images.load(str(image_path), check_existing=True)
        node_tree = bpy_material.node_tree
        image_texture = node_tree.nodes.new("ShaderNodeTexImage")
        image_texture.image = image  # type: ignore[attr-defined]
        image_texture.extension = "CLIP"  # type: ignore[attr-defined]
        bsdf = node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Specular"].default_value = 0  # type: ignore[attr-defined]
        node_tree.links.new(image_texture.outputs["Color"], bsdf.inputs["Base Color"])
        node_tree.links.new(image_texture.outputs["Alpha"], bsdf.inputs["Alpha"])
        if resource.additive:
            bpy_material.blend_method = "BLEND"
        else:
            bpy_material.blend_method = "CLIP"
        bpy_material.alpha_threshold = 0
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
            vertices=list(mesh.vertices),
            edges=[],
            faces=[polygon.face for polygon in mesh.polygons],
        )
        return bpy_mesh

    def set_object_location(self, obj: bpy.types.Object, location: Vector3d) -> None:
        mu_location = mathutils.Vector(location)
        obj.location = mu_location

    def set_object_animation(self, obj: bpy.types.Object, animation: Animation) -> None:
        obj.rotation_mode = "QUATERNION"
        for index, (location, quaternion) in enumerate(
            zip(animation.locations, animation.quaternions)
        ):
            mu_location = mathutils.Vector(location)
            mu_quaternion = mathutils.Quaternion(quaternion)
            mu_quaternion = mu_quaternion.normalized()
            mu_quaternion = mu_quaternion.inverted()
            obj.location = mu_location
            obj.rotation_quaternion = mu_quaternion  # type: ignore[assignment]
            obj.keyframe_insert(data_path="location", frame=index * animation.delay)
            obj.keyframe_insert(data_path="rotation_quaternion", frame=index * animation.delay)
        obj.animation_data.action.name = f"{obj.name}-loop"

    def make_drawable_object(self, name: str, mesh: DrawableMesh) -> bpy.types.Object:
        bpy_mesh = self.make_base_mesh(name=name, mesh=mesh)
        uv_layer = bpy_mesh.uv_layers.new()
        uvs = collapse(polygon.uv for polygon in mesh.polygons)
        uv_layer.data.foreach_set("uv", list(uvs))
        if mesh.normals:
            normals = tuple(mesh.normals)
            # I have no idea if setting the normals even works
            bpy_mesh.normals_split_custom_set_from_vertices(normals)  # type: ignore[arg-type]
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
        return bpy_obj

    def make_light_object(self, name: str, light: Light) -> bpy.types.Object:
        bpy_light = bpy.data.lights.new(name=name, type="POINT")
        bpy_light.color = light.attributes.color.rgb_float
        bpy_light.use_custom_distance = True
        bpy_light.cutoff_distance = 15.0
        bpy_light.specular_factor = 0.2
        bpy_light.energy = 500  # type: ignore[attr-defined]
        bpy_light.use_shadow = False  # type: ignore[attr-defined]
        bpy_obj = bpy.data.objects.new(name=name, object_data=bpy_light)
        self.set_object_location(obj=bpy_obj, location=light.location)
        return bpy_obj


class TrackImportStrategy(metaclass=ABCMeta):
    @abstractmethod
    def import_track(self, track: TrackData) -> None:
        pass


class TrackImportSimple(TrackImportStrategy, BaseImporter):
    def import_track(self, track: TrackData) -> None:
        track_collection = bpy.data.collections.new("Track segments")
        bpy.context.scene.collection.children.link(track_collection)
        for index, segment in enumerate(track.track_segments):
            name = f"Track segment {index}"
            bpy_obj = self.make_drawable_object(name=name, mesh=segment.mesh)
            track_collection.objects.link(bpy_obj)
        for index, obj in enumerate(track.objects):
            name = f"Track object {index}"
            bpy_obj = self.make_drawable_object(name=name, mesh=obj.mesh)
            if obj.location:
                self.set_object_location(obj=bpy_obj, location=obj.location)
            if obj.animation:
                self.set_object_animation(obj=bpy_obj, animation=obj.animation)
            track_collection.objects.link(bpy_obj)
        for index, light in enumerate(track.lights):
            name = f"Track light {index}"
            bpy_obj = self.make_light_object(name=name, light=light)
            track_collection.objects.link(bpy_obj)


class TrackImportAdvanced(TrackImportStrategy, BaseImporter):
    def import_track(self, track: TrackData) -> None:
        track_collection = bpy.data.collections.new("Track segments")
        bpy.context.scene.collection.children.link(track_collection)
        for index, segment in enumerate(track.track_segments):
            name = f"Track segment {index}"
            bpy_obj = self.make_drawable_object(name=name, mesh=segment.mesh)
            track_collection.objects.link(bpy_obj)
            for collision_mesh in segment.collision_meshes:
                name = (
                    f"Track segment collission {index}.{collision_mesh.collision_effect}-colonly"
                )
                bpy_mesh = self.make_base_mesh(name=name, mesh=collision_mesh)
                bpy_obj = bpy.data.objects.new(name, bpy_mesh)
                track_collection.objects.link(bpy_obj)
                bpy_obj.hide_set(True)
        for index, obj in enumerate(track.objects):
            name = f"Track object {index}"
            bpy_obj = self.make_drawable_object(name=name, mesh=obj.mesh)
            if obj.location:
                self.set_object_location(obj=bpy_obj, location=obj.location)
            if obj.animation:
                self.set_object_animation(obj=bpy_obj, animation=obj.animation)
            track_collection.objects.link(bpy_obj)
        for index, light in enumerate(track.lights):
            name = f"Track light {index}"
            bpy_obj = self.make_light_object(name=name, light=light)
            track_collection.objects.link(bpy_obj)


class CarImporterSimple(BaseImporter):
    def import_car(self, parts: Iterable[Part]) -> None:
        car_collection = bpy.data.collections.new("Car parts")
        bpy.context.scene.collection.children.link(car_collection)
        for part in parts:
            bpy_obj = self.make_drawable_object(name=part.name, mesh=part.mesh)
            self.set_object_location(obj=bpy_obj, location=part.location)
            car_collection.objects.link(bpy_obj)


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
                "SIMPLE",
                "Simple",
                "Import only visible track geometry, lights and animations.",
            ),
            (
                "ADVANCED",
                "Advanced (experimental)",
                "Parametrized import of visible track geometry, lights, animations, "
                "collision geometry and more",
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

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[int] | set[str]:
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context) -> set[int] | set[str]:
        track = TrackData(
            directory=self.directory,
            mirrored=self.mirrored,
            night=self.night,
            weather=self.weather,
        )
        import_strategy: TrackImportStrategy
        if self.mode == "SIMPLE":
            import_strategy = TrackImportSimple(material_map=track.get_polygon_material)
        elif self.mode == "ADVANCED":
            import_strategy = TrackImportAdvanced(material_map=track.get_polygon_material)
        else:
            return {"CANCELLED"}
        import_strategy.import_track(track=track)
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

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[int] | set[str]:
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context) -> set[int] | set[str]:
        car = VivData.from_file(Path(self.directory, "CAR.VIV"))
        logger.debug(car)

        resource = next(car.body_materials)
        importer = CarImporterSimple(material_map=lambda _: resource)
        importer.import_car(car.parts)

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
