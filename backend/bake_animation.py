import bpy
import json
import os
import sys

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AVATAR_FILE = "avatar.glb" 
KEYPOINTS_FILE = "car_keypoints.json" 
OUTPUT_FILE = "car_rotations.json"

# --- BONE MAPPING (CRITICAL!) ---
# Updated with your "mixamorig:BoneName" convention.
KEYPOINT_MAP = {
    # MediaPipe Index: IK Target Name (Empty)
    15: "IK_Target_Left",      # LEFT_WRIST
    16: "IK_Target_Right",     # RIGHT_WRIST
    13: "Pole_Target_Left",    # LEFT_ELBOW
    14: "Pole_Target_Right"    # RIGHT_ELBOW
}

# Bones in the IK chain (from hand up to shoulder)
LEFT_IK_CHAIN_BONES = ["mixamorig:LeftHand", "mixamorig:LeftForeArm", "mixamorig:LeftArm"]
RIGHT_IK_CHAIN_BONES = ["mixamorig:RightHand", "mixamorig:RightForeArm", "mixamorig:RightArm"]

# Body bones to animate (will be baked even without IK)
BODY_BONES = ["mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Spine2", "mixamorig:Neck", "mixamorig:Head"]

# Map of which IK bone gets which pole target
# (IK Bone Name): (Pole Target Name, Pole Bone Name)
POLE_TARGET_MAP = {
    "mixamorig:LeftHand": ("Pole_Target_Left", "mixamorig:LeftForeArm"),
    "mixamorig:RightHand": ("Pole_Target_Right", "mixamorig:RightForeArm")
}
# ---

def clear_scene():
    """Deletes all objects from the default Blender scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
def get_keypoint(frame_data, index):
    """Extracts a 3D vector from the flat 99-float keypoint list."""
    base = index * 3
    if frame_data and len(frame_data) > base + 2:
        # Assumes MediaPipe world landmarks (x, -y, z) mapping
        # Blender: (X, Y, Z)
        x = frame_data[base]
        y = frame_data[base + 1]
        z = frame_data[base + 2]
        # This transform depends on your GLB export/import settings.
        # This is the most common mapping from MP world to Blender:
        return (x, z, -y) 
    return (0, 0, 0)

def setup_ik_constraint(armature, bone_name, target_obj, pole_target_obj, pole_bone_name, chain_count=3):
    """Adds an IK constraint to a bone."""
    print(f"Setting up IK for: {bone_name}")
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    bone = armature.pose.bones.get(bone_name)
    if not bone:
        print(f"Error: Bone '{bone_name}' not found in armature.")
        return None

    constraint = bone.constraints.new(type='IK')
    constraint.target = target_obj
    constraint.chain_count = chain_count
    
    # Add Pole Target
    if pole_target_obj and pole_bone_name:
        constraint.pole_target = pole_target_obj
        constraint.pole_subtarget = pole_bone_name
        constraint.pole_angle = -1.5708 # -90 degrees in radians, often needed for Mixamo
        
    bpy.ops.object.mode_set(mode='OBJECT')
    return constraint

def check_bone_names(armature):
    """Checks if all required bones exist in the armature."""
    print("Checking bone names...")
    all_bones_needed = LEFT_IK_CHAIN_BONES + RIGHT_IK_CHAIN_BONES + BODY_BONES
    missing_bones = []
    
    armature_bone_names = armature.data.bones.keys()
    
    for bone_name in all_bones_needed:
        if bone_name not in armature_bone_names:
            missing_bones.append(bone_name)
            
    if missing_bones:
        print("\n--- ERROR: MISSING BONES ---")
        print("The following bones specified in the script were NOT found in your avatar:")
        for name in missing_bones:
            print(f" - {name}")
        print("\nPlease correct the bone name lists at the top of the script.")
        print("Available bones in your model:")
        for name in armature_bone_names:
            print(f"  {name}")
        print("----------------------------\n")
        return False
    
    print("✅ All specified bones found in armature.")
    return True

def animate_ik_targets(keypoint_frames):
    """Creates and animates the IK target Empties."""
    print("Creating and animating IK targets...")
    ik_targets = {}
    
    # Create Empties for all targets
    for index, name in KEYPOINT_MAP.items():
        bpy.ops.object.empty_add(type='SPHERE', radius=0.05)
        target_obj = bpy.context.object
        target_obj.name = name
        ik_targets[name] = target_obj
        
    # Keyframe the Empties
    for frame_num in range(len(keypoint_frames)):
        bpy.context.scene.frame_set(frame_num)
        frame_data = keypoint_frames[frame_num]
        
        for index, name in KEYPOINT_MAP.items():
            target_obj = ik_targets[name]
            target_pos = get_keypoint(frame_data, index)
            
            target_obj.location = target_pos
            target_obj.keyframe_insert(data_path="location", frame=frame_num)
            
    return ik_targets

def main():
    print("--- Starting Animation Bake Script ---")
    
    # 1. Setup Scene
    clear_scene()
    bpy.context.scene.frame_start = 0
    
    # 2. Load Avatar
    avatar_path = os.path.join(SCRIPT_DIR, AVATAR_FILE)
    if not os.path.exists(avatar_path):
        print(f"Error: Avatar file not found at {avatar_path}")
        return
    bpy.ops.import_scene.gltf(filepath=avatar_path)
    armature = next((obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE'), None)
    
    if not armature:
        print(f"Error: No armature found in {AVATAR_FILE}")
        return
    print(f"Loaded armature: {armature.name}")
    
    # 3. Check Bone Names
    if not check_bone_names(armature):
        return # Stop if bones are missing

    # 4. Load Keypoint Data
    keypoints_path = os.path.join(SCRIPT_DIR, KEYPOINTS_FILE)
    if not os.path.exists(keypoints_path):
        print(f"Error: Keypoints file not found at {keypoints_path}")
        return
    with open(keypoints_path, 'r') as f:
        keypoint_frames = json.load(f)
    num_frames = len(keypoint_frames)
    bpy.context.scene.frame_end = num_frames - 1
    print(f"Loaded {num_frames} frames from {KEYPOINTS_FILE}")

    # 5. Create and Animate IK Targets
    ik_targets = animate_ik_targets(keypoint_frames)
    
    # 6. Add IK Constraints
    setup_ik_constraint(armature, 
                        "mixamorig:LeftHand", 
                        ik_targets["IK_Target_Left"], 
                        ik_targets["Pole_Target_Left"], 
                        POLE_TARGET_MAP["mixamorig:LeftHand"][1])
                        
    setup_ik_constraint(armature, 
                        "mixamorig:RightHand", 
                        ik_targets["IK_Target_Right"], 
                        ik_targets["Pole_Target_Right"],
                        POLE_TARGET_MAP["mixamorig:RightHand"][1])
    
    # 7. Bake the Animation
    print("Baking animation to all bones...")
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    # Select *all* bones we want to export
    all_bones_to_bake = list(set(LEFT_IK_CHAIN_BONES + RIGHT_IK_CHAIN_BONES + BODY_BONES))
    
    for bone in armature.data.bones:
        bone.select = bone.name in all_bones_to_bake
            
    bpy.ops.nla.bake(
        frame_start=0,
        frame_end=num_frames - 1,
        visual_keying=True,       # Bake the final visual rotation
        clear_constraints=True,   # Remove the IK constraints
        bake_types={'POSE'}
    )
    
    # 8. Export the Baked Rotations
    print("Exporting baked rotation data...")
    final_animation_frames = []
    
    # Get a stable list of all bones in the armature, in order
    all_pose_bones = list(armature.pose.bones)
    
    for frame_num in range(num_frames):
        bpy.context.scene.frame_set(frame_num)
        
        frame_data = {"bones": []}
        for bone in all_pose_bones:
            # Get the bone's rotation in its local space
            q = bone.rotation_quaternion
            # Store as [w, x, y, z]
            frame_data["bones"].append([q.w, q.x, q.y, q.z])
            
        final_animation_frames.append(frame_data)
        
    # 9. Save to Output File
    output_path = os.path.join(SCRIPT_DIR, OUTPUT_FILE)
    with open(output_path, 'w') as f:
        json.dump(final_animation_frames, f)
        
    print(f"\n✅ Success! Baked {num_frames} frames for {len(all_pose_bones)} bones.")
    print(f"Saved final animation to: {OUTPUT_FILE}")

if __name__ == "__main__":
    # This allows running from command line: blender -b --python bake_animation.py
    main()