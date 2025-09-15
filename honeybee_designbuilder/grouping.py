# coding=utf-8
"""Methods for grouping rooms to comply with INP rules."""
from __future__ import division
import math

from ladybug_geometry.geometry2d import Point2D, Polygon2D
from ladybug_geometry.geometry3d import Vector3D, Point3D, Face3D
from honeybee.typing import clean_doe2_string
from honeybee.room import Room

from .config import DOE2_TOLERANCE, FLOOR_LEVEL_TOL, RES_CHARS


def group_rooms_by_block(rooms, model_tolerance):
    """Group Honeybee Rooms according to acceptable floor levels in DOE-2.

    This means that not only will Rooms be on separate DOE-2 levels if their floor
    heights differ but also Rooms that share the same floor height but are
    disconnected from one another in plan will also be separate levels.
    For example, when the model is of two towers on a plinth, each tower will
    get its own separate level group.

    Args:
        rooms: A list of Honeybee Rooms to be grouped.
        model_tolerance: The tolerance of the model that the Rooms originated from.

    Returns:
        A tuple with three elements.

        -   room_groups: A list of lists where each sub-list contains Honeybee
            Rooms that should be on the same DOE-2 level.

        -   level_geometries: A list of Face3D with the same length as the
            room_groups, which contains the geometry that represents each floor
            level. These geometries will always be pointing upwards so that
            their vertices are counter-clockwise when viewed from above. They
            will also have colinear vertices removed such that they are ready
            to be translated to INP POLYGONS.

        -   level_names: A list of text strings that align with the level
            geometry and contain suggested names for the DOE-2 levels.
    """
    # set up lists of the outputs to be populated
    room_groups, level_geometries, level_names, existing_levels = [], [], [], {}

    # first group the rooms by floor height
    grouped_rooms, _ = Room.group_by_floor_height(rooms, FLOOR_LEVEL_TOL)
    for fi, room_group in enumerate(grouped_rooms):
        # determine a base name for the level using the story assigned to the rooms
        level_name = clean_doe2_string(room_group[0].story, RES_CHARS - 8) \
            if room_group[0].story is not None else 'Level_{}'.format(fi)
        if level_name in existing_levels:
            existing_levels[level_name] += 1
            level_name = level_name + str(existing_levels[level_name])
        else:
            existing_levels[level_name] = 1

        # then, group the rooms by contiguous horizontal boundary
        floor_geos = []
        for room in room_group:
            if room.properties.doe2.space_polygon_geometry is not None:
                floor_geos.append(room.properties.doe2.space_polygon_geometry)
            else:
                try:
                    flr_geo = room.horizontal_floor_boundaries(tolerance=model_tolerance)
                    if len(flr_geo) == 0:  # possible when Rooms have no floors
                        flr_geo = room.horizontal_boundary(tolerance=model_tolerance)
                        floor_geos.append(flr_geo)
                    else:
                        floor_geos.extend(flr_geo)
                except Exception:  # level geometry is overlapping or not clean
                    pass

        # join all of the floors into horizontal boundaries
        hor_bounds = _grouped_floor_boundary(floor_geos, model_tolerance)

        # if we got lucky and everything is one contiguous polygon, we're done!
        if len(hor_bounds) == 0:  # we will write the story with NO-SHAPE
            room_groups.append(room_group)
            level_geometries.append(None)
            level_names.append(level_name)
        elif len(hor_bounds) == 1:  # just one clean polygon for the level
            flr_geo = hor_bounds[0]
            flr_geo = flr_geo if flr_geo.normal.z >= 0 else flr_geo.flip()
            if flr_geo.has_holes:  # remove holes as we only care about the boundary
                flr_geo = Face3D(flr_geo.boundary, flr_geo.plane)
            flr_geo = flr_geo.remove_colinear_vertices(tolerance=DOE2_TOLERANCE)
            room_groups.append(room_group)
            level_geometries.append(flr_geo)
            level_names.append(level_name)
        else:  # we need to figure out which Room belongs to which geometry
            # first get a set of Point2Ds that are inside each room in plan
            room_pts, z_axis = [], Vector3D(0, 0, 1)
            for room in room_group:
                for face in room.faces:
                    if math.degrees(z_axis.angle(face.normal)) >= 91:
                        down_geo = face.geometry
                        break
                room_pt3d = down_geo.center if down_geo.is_convex else \
                    down_geo.pole_of_inaccessibility(DOE2_TOLERANCE)
                room_pts.append(Point2D(room_pt3d.x, room_pt3d.y))
            # loop through floor geometries and determine all rooms associated with them
            for si, flr_geo in enumerate(hor_bounds):
                flr_geo = flr_geo if flr_geo.normal.z >= 0 else flr_geo.flip()
                if flr_geo.has_holes:  # remove holes as we only care about the boundary
                    flr_geo = Face3D(flr_geo.boundary, flr_geo.plane)
                flr_geo = flr_geo.remove_colinear_vertices(tolerance=DOE2_TOLERANCE)
                flr_poly = Polygon2D([Point2D(pt.x, pt.y) for pt in flr_geo.boundary])
                flr_rooms = []
                for room, room_pt in zip(room_group, room_pts):
                    if flr_poly.is_point_inside_bound_rect(room_pt):
                        flr_rooms.append(room)
                room_groups.append(flr_rooms)
                level_geometries.append(flr_geo)
                level_names.append('{}_Section{}'.format(level_name, si))

    # return all of the outputs
    return room_groups, level_geometries, level_names
