from ultralytics import YOLO
import supervision as sv
import numpy as np
import pickle
import os
import sys
import cv2

sys.path.append("../")
from utils import get_bbox_center, get_bbox_width


class Tracker:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.tracker = sv.ByteTrack()
    
    def detect_frames(self, frames):
        batch_size = 20
        detections = []
        for i in range(0, len(frames), batch_size):
            detections_batch = self.model.predict(frames[i:i+batch_size], conf=0.3)
            detections.extend(detections_batch)
        
        print(f"Total detections returned: {len(detections)}")
        return detections
    
    
    def get_object_tracks(self, frames, read_from_stub=False, stub_path=None):
        
        if read_from_stub and stub_path is not None and os.path.exists(stub_path):
            with open(stub_path, "rb") as f:
                tracks = pickle.load(f)
            print(f"Loaded tracks from stub with {len(tracks['players'])} frames")
            return tracks
        
        detections = self.detect_frames(frames)
        print(f"Detected {len(detections)} frames from {len(frames)} input frames")
        
        tracks = {
            "players": [],
            "referees": [],
            "ball": [],
        }
        
        for frame_num, detections in enumerate(detections):
            cls_names = detections.names
            cls_names_inv = {v:k for k, v in cls_names.items()} # Inverse mapping 
            print(cls_names)
            
            detection_sv = sv.Detections.from_ultralytics(detections)
            
            for idx, class_id in enumerate(detection_sv.class_id):
                if cls_names[class_id] == "goalkeeper":
                    detection_sv.class_id[idx] = cls_names_inv["player"]
                    
            detection_with_tracker = self.tracker.update_with_detections(detection_sv)
            
            tracks["players"].append({}) 
            tracks["referees"].append({})
            tracks["ball"].append({})
            
            for frame in detection_with_tracker:
                bbox = frame[0].tolist()
                cls_id = frame[3]
                track_id = frame[4]
                print(f"Frame {frame_num}, Class: {cls_names[cls_id]}, Track ID: {track_id}")
                
                if cls_id == cls_names_inv["player"]:
                    tracks["players"][frame_num][track_id] = {"bbox": bbox}
                    
                if cls_id == cls_names_inv["referee"]:
                    tracks["referees"][frame_num][track_id] = {"bbox": bbox}
                 
            for frame in detection_sv:
                bbox = frame[0].tolist()
                cls_id = frame[3]
                
                if cls_id == cls_names_inv["ball"]:
                    tracks["ball"][frame_num][1] = {"bbox": bbox}
            
            
        if stub_path is not None:
            with open(stub_path, "wb") as f:
                pickle.dump(tracks, f)
                
        return tracks
        
        
    def draw_elipse(self, frame, bbox, color, track_id=None):
        y2 = int(bbox[3])
        x_center, _ = get_bbox_center(bbox)
        width = get_bbox_width(bbox)
        
        cv2.ellipse(
            frame,
            center = (x_center, y2),
            axes = (int(width), int(0.35*width)),
            angle = 0.0,
            startAngle = -45,
            endAngle = 235,
            color = color,
            thickness = 2,
            lineType = cv2.LINE_4
        )
        
        
        rectangle_width = 40
        rectangle_height = 20
        
        x1_rect = x_center - rectangle_width // 2
        x2_rect = x_center + rectangle_width // 2
        
        y1_rect = (y2 - rectangle_height // 2) + 15
        y2_rect = (y2 + rectangle_height // 2) + 15
        
        if track_id is not None:
            cv2.rectangle(
                frame,
                (int(x1_rect), int(y1_rect)),
                (int(x2_rect), int(y2_rect)),
                color,
                cv2.FILLED
            )
          
            x1_text = x1_rect + 12
            if track_id > 99:
                x1_text -=10
          
            cv2.putText(
                frame,
                f"{track_id}",
                (int(x1_text), int(y1_rect+15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2
          )
            
        return frame
        
    
    def draw_traingle(self, frame, bbox, color):
        y = int(bbox[1])
        x, _ = get_bbox_center(bbox)
        
        triangle_points = np.array([
            [x, y],
            [x-10, y-20],
            [x+10, y-20],
            
        ])
        
        cv2.drawContours(frame, [triangle_points], 0, color, cv2.FILLED)
        cv2.drawContours(frame, [triangle_points], 0, (0, 0, 0), 2)
        
        return frame
        
        
    def draw_annotations(self, video_frames, tracks):
        output_video_frames = []
        print(f"Number of video frames: {len(video_frames)}")
        print(f"Number of player tracks: {len(tracks['players'])}")
        print(f"Number of referee tracks: {len(tracks['referees'])}")
        print(f"Number of ball tracks: {len(tracks['ball'])}")
        
        for frame_num, frame in enumerate(video_frames):
            frame = frame.copy()
            
            player_dict = tracks["players"][frame_num]
            ball_dict = tracks["ball"][frame_num]
            referee_dict = tracks["referees"][frame_num]

            # Draw players
            for track_id, player in player_dict.items():
                frame = self.draw_elipse(frame, player["bbox"], (0, 0, 255), track_id)
                
            for _, referee in referee_dict.items():
                frame = self.draw_elipse(frame, referee["bbox"], (0, 255, 255))
                
            for _, ball in ball_dict.items():
                frame = self.draw_traingle(frame, ball["bbox"], (0, 255, 0))
                
                
            output_video_frames.append(frame)
        
        return output_video_frames
