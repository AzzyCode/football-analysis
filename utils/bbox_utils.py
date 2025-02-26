
def get_bbox_center(bbox):
    # bbox [x1, y1, x2, y2]
    center_x = int((bbox[2] + bbox[0]) / 2)
    center_y = int((bbox[1] + bbox[3]) / 2)
    
    return center_x, center_y


def get_bbox_width(bbox):
    return bbox[2] - bbox[0]



