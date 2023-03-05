import logging
from pathlib import Path

import bpy
import mathutils
from bpy.props import StringProperty

from speedtools import TrackData, VivData

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
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


class IMPORT_TRACK_track(bpy.types.Operator):
    """Import NFS4 Track Operator"""

    bl_idname = "import_scene.nfs4trk"
    bl_label = "Import NFS4 Track"
    bl_description = "Import NFS4 track files"
    bl_options = {"REGISTER", "UNDO"}

    bpy.types.Scene.nfs4trk = None

    directory: StringProperty(
        name="Directory Path",
        description="Directory containing the track files",
        maxlen=1024,
        default="",
    )

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        track = TrackData(self.directory)

        images_dir = bpy.path.abspath("//images")

        materials = {}
        for material in track.material_ids:
            bpy_material = bpy.data.materials.new(str(material))
            bpy_material.use_nodes = True
            materials[material] = bpy_material
            image_path = Path(images_dir, f"{str(int(material)+2).zfill(4)}.png")
            image = bpy.data.images.load(str(image_path))
            node_tree = bpy_material.node_tree
            image_texture = node_tree.nodes.new("ShaderNodeTexImage")
            image_texture.image = image
            image_texture.extension = "CLIP"
            bsdf = node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Specular"].default_value = 0
            node_tree.links.new(image_texture.outputs["Color"], bsdf.inputs["Base Color"])
            node_tree.links.new(image_texture.outputs["Alpha"], bsdf.inputs["Alpha"])
            bpy_material.blend_method = "CLIP"
            bpy_material.alpha_threshold = 0

        track_collection = bpy.data.collections.new("Track segments")
        bpy.context.scene.collection.children.link(track_collection)

        for index, segment in enumerate(track.track_segments):
            name = f"Track segment {index}"
            faces = [polygon.face for polygon in segment.polygons]
            mesh = bpy.data.meshes.new(f"{name}-col")
            mesh.from_pydata(vertices=segment.vertices, edges=[], faces=faces)
            logger.debug(f"vertices: {segment.vertices}")
            mesh.validate()
            uv_layer = mesh.uv_layers.new()
            uv_layer.name = f"{name} UV"
            for index, (track_polygon, bpy_polygon) in enumerate(
                zip(segment.polygons, mesh.polygons, strict=True)
            ):
                logger.debug(f"index: {index}, polygon {track_polygon}")
                bpy_polygon.use_smooth = True
                for uv, loop_indice in zip(
                    track_polygon.uv, bpy_polygon.loop_indices, strict=True
                ):
                    uv_layer.data[loop_indice].uv = uv
                material = materials[track_polygon.material]
                material.use_backface_culling = track_polygon.backface_culling
                mesh.materials.append(material)
                bpy_polygon.material_index = index

            bpy_obj = bpy.data.objects.new(name, mesh)
            track_collection.objects.link(bpy_obj)

        for index, object in enumerate(track.objects):
            name = f"Track object {index}-rigid"
            collection = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(collection)
            faces = [polygon.face for polygon in object.polygons]
            mesh = bpy.data.meshes.new(f"{name}")
            mesh.from_pydata(vertices=object.vertices, edges=[], faces=faces)
            mesh.validate()
            uv_layer = mesh.uv_layers.new()
            uv_layer.name = f"{name} UV"
            for index, (track_polygon, bpy_polygon) in enumerate(
                zip(object.polygons, mesh.polygons, strict=True)
            ):
                bpy_polygon.use_smooth = True
                for uv, loop_indice in zip(
                    track_polygon.uv, bpy_polygon.loop_indices, strict=True
                ):
                    uv_layer.data[loop_indice].uv = uv
                material = materials[track_polygon.material]
                material.use_backface_culling = track_polygon.backface_culling
                mesh.materials.append(material)
                bpy_polygon.material_index = index

            bpy_obj = bpy.data.objects.new(name, mesh)
            collection.objects.link(bpy_obj)
            bpy.context.view_layer.objects.active = bpy_obj
            if object.position is not None:
                pos = mathutils.Vector(object.position)
                bpy_obj.location += pos
            if object.animation is not None:
                bpy_obj.rotation_mode = "QUATERNION"
                animation = object.animation
                for index, (position, quaternion) in enumerate(
                    zip(animation.positions, animation.quaternions)
                ):
                    mu_position = mathutils.Vector(position)
                    mu_quaternion = mathutils.Quaternion(quaternion)
                    mu_quaternion.normalize()
                    mu_quaternion.invert()
                    bpy_obj.location = mu_position
                    bpy_obj.rotation_quaternion = mu_quaternion
                    bpy_obj.keyframe_insert(data_path="location", frame=index * 16)
                    bpy_obj.keyframe_insert(data_path="rotation_quaternion", frame=index * 16)

            bpy_obj.asset_mark()
            bpy_obj.asset_generate_preview()

        return {"FINISHED"}


class IMPORT_CAR_car(bpy.types.Operator):
    """Import NFS4 Car Operator"""

    bl_idname = "import_scene.nfs4car"
    bl_label = "Import NFS4 Car"
    bl_description = "Import NFS4 Car files"
    bl_options = {"REGISTER", "UNDO"}

    bpy.types.Scene.nfs4car = None

    directory: StringProperty(
        name="Directory Path",
        description="Directory containing the car files",
        maxlen=1024,
        default="",
    )

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        car = VivData.from_file(Path(self.directory, "CAR.VIV"))
        logger.debug(car)

        images_dir = bpy.path.abspath("//images")

        filtered_parts = (
            5,
            6,
            7,
            14,
            15,
            16,
            17,
        )  # TODO: Figure out better way to filter low poly parts

        car_collection = bpy.data.collections.new("Car parts")
        bpy.context.scene.collection.children.link(car_collection)

        materials = {}
        for material in car.materials:
            bpy_material = bpy.data.materials.new(material)
            bpy_material.use_nodes = True
            bpy_material.use_backface_culling = True
            materials[material] = bpy_material
            image_path = Path(images_dir, material)
            image = bpy.data.images.load(str(image_path))
            node_tree = bpy_material.node_tree
            image_texture = node_tree.nodes.new("ShaderNodeTexImage")
            image_texture.image = image
            image_texture.extension = "CLIP"
            bsdf = node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Specular"].default_value = 0
            node_tree.links.new(image_texture.outputs["Color"], bsdf.inputs["Base Color"])
            node_tree.links.new(image_texture.outputs["Alpha"], bsdf.inputs["Alpha"])
            bpy_material.blend_method = "CLIP"
            bpy_material.alpha_threshold = 0

        for index, part in enumerate(car.parts):
            if index in filtered_parts:
                continue
            name = f"Car part {index}"
            faces = [polygon.face for polygon in part.polygons]
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(vertices=part.vertices, edges=[], faces=faces)
            uv_layer = mesh.uv_layers.new()
            uv_layer.name = f"{name} UV"
            mesh.use_auto_smooth = True
            for index, (car_polygon, bpy_polygon) in enumerate(
                zip(part.polygons, mesh.polygons, strict=True)
            ):
                for uv, loop_indice in zip(car_polygon.uv, bpy_polygon.loop_indices, strict=True):
                    uv_layer.data[loop_indice].uv = uv
                    # TODO: Figure out vertex normals
                    # vertex_index = mesh.loops[loop_indice].vertex_index
                    # mesh.loops[loop_indice].normal[:] = part.normals[vertex_index]
            material = materials["car00.tga"]
            mesh.materials.append(material)
            mesh.validate()
            bpy_obj = bpy.data.objects.new(name, mesh)
            car_collection.objects.link(bpy_obj)
            pos = mathutils.Vector(part.position)
            bpy_obj.location += pos

        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(IMPORT_TRACK_track.bl_idname, text="Track resources")
    self.layout.operator(IMPORT_CAR_car.bl_idname, text="Car resources")


def register():
    bpy.utils.register_class(IMPORT_TRACK_track)
    bpy.utils.register_class(IMPORT_CAR_car)
    bpy.types.TOPBAR_MT_file_import.append(menu_func)


def unregister():
    bpy.utils.unregister_class(IMPORT_TRACK_track)
    bpy.utils.unregister_class(IMPORT_CAR_car)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func)


if __name__ == "__main__":
    register()
