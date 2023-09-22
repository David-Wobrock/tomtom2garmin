import json
import os
import sys
from datetime import datetime
from typing import Optional

import gpxpy
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from gpxpy.gpx import GPX
from garmin_fit_sdk import Decoder, Stream


from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.profile_type import (
    Sport,
    Manufacturer,
    FileType,
    ActivityType,
    Event,
    EventType,
    SubSport,
)

OUTPUT_DIRECTORY = "output"


def read_gpx_file(filename: str) -> GPX:
    with open(filename, "r") as gpx_file:
        return gpxpy.parse(gpx_file)


def read_json_file(filename: str) -> dict:
    with open(filename, "r") as json_file:
        return json.load(json_file)


def gpx_to_fit(gpx: GPX, fit_filename: str):
    record_messages = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                record_msg = RecordMessage()
                record_msg.position_lat = point.latitude
                record_msg.position_long = point.longitude
                record_msg.altitude = point.elevation
                record_msg.timestamp = int(point.time.timestamp() * 1000)
                if point.extensions:
                    record_msg.heart_rate = int(
                        point.extensions[0]
                        .find(
                            "{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}hr"
                        )
                        .text
                    )
                record_messages.append(record_msg)

    if fit_filename.startswith("cycling_"):
        activity_type = ActivityType.CYCLING
        sport = Sport.CYCLING
    elif fit_filename.startswith("hiking_"):
        activity_type = ActivityType.RUNNING
        sport = Sport.HIKING
    elif fit_filename.startswith("running_"):
        activity_type = ActivityType.RUNNING
        sport = Sport.RUNNING
    else:
        ValueError(f"Unhandled GPX activity {fit_filename}")

    create_activity_file(fit_filename, record_messages, activity_type, sport)


def json_to_fit(json_data: dict, fit_filename: str):
    if fit_filename.startswith("tracking_"):
        # Ignoring these files, since they represent only tracking steps.
        return

    record_messages = []
    start_timestamp = datetime.fromisoformat(json_data["start_datetime"]).timestamp()
    for second, heart_rate in json_data["time_series"]["heartrate"]:
        record_msg = RecordMessage()
        record_msg.timestamp = (start_timestamp + second) * 1000
        record_msg.heart_rate = int(heart_rate)
        record_messages.append(record_msg)

    if fit_filename.startswith("gym_"):
        activity_type = ActivityType.GENERIC
        sport = Sport.TRAINING
        subsport = SubSport.CARDIO_TRAINING
    elif fit_filename.startswith("indoor_cycling_"):
        activity_type = ActivityType.CYCLING
        sport = Sport.CYCLING
        subsport = SubSport.INDOOR_CYCLING
    elif fit_filename.startswith("treadmill_"):
        activity_type = ActivityType.RUNNING
        sport = Sport.RUNNING
        subsport = SubSport.TREADMILL
    else:
        ValueError(f"Unhandled json_2 activity {fit_filename}")

    create_activity_file(fit_filename, record_messages, activity_type, sport, subsport)


def assert_fit_integrity(filename: str) -> None:
    stream = Stream.from_file(filename)
    decoder = Decoder(stream)
    assert decoder.is_fit()
    assert decoder.check_integrity()


def main(input_directory):
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    for root, _, files in os.walk(input_directory):
        for filename in files:
            print(f"Handling {filename} ...")
            if filename.endswith(".gpx"):
                gpx = read_gpx_file(os.path.join(root, filename))
                fit_filename = filename.replace(".gpx", ".fit")
                gpx_to_fit(gpx, fit_filename)
            elif filename.endswith(".json_2"):
                json_data = read_json_file(os.path.join(root, filename))
                fit_filename = filename.replace(".json_2", ".fit")
                json_to_fit(json_data, fit_filename)


def create_activity_file(
    filename: str,
    record_messages: list[RecordMessage],
    activity_type: ActivityType,
    sport: Sport,
    subsport: Optional[SubSport] = None,
):
    start_timestamp = record_messages[0].timestamp
    end_timestamp = record_messages[-1].timestamp
    total_time = (end_timestamp - start_timestamp) / 1000
    is_gpx_activity = any(record_msg.position_lat for record_msg in record_messages)

    min_heart_rate = min(
        record_msg.heart_rate for record_msg in record_messages if record_msg.heart_rate
    )
    max_heart_rate = max(
        record_msg.heart_rate for record_msg in record_messages if record_msg.heart_rate
    )
    avg_heart_rate = sum(
        record_msg.heart_rate for record_msg in record_messages if record_msg.heart_rate
    ) / len(record_messages)

    if is_gpx_activity:
        min_altitude = min(
            record_msg.altitude for record_msg in record_messages if record_msg.altitude
        )
        max_altitude = max(
            record_msg.altitude for record_msg in record_messages if record_msg.altitude
        )
        avg_altitude = sum(
            record_msg.altitude for record_msg in record_messages if record_msg.altitude
        ) / len(record_messages)

    file_id_msg = FileIdMessage()
    file_id_msg.type = FileType.ACTIVITY
    file_id_msg.manufacturer = Manufacturer.TOMTOM
    file_id_msg.product_name = "TomTom Adventurer"  # My sports watch
    file_id_msg.time_created = start_timestamp

    event_timer_start_msg = EventMessage()
    event_timer_start_msg.event = Event.TIMER
    event_timer_start_msg.event_type = EventType.START
    event_timer_start_msg.timestamp = start_timestamp

    event_timer_stop_msg = EventMessage()
    event_timer_stop_msg.event = Event.TIMER
    event_timer_stop_msg.event_type = EventType.STOP_ALL
    event_timer_stop_msg.timestamp = end_timestamp

    lap_msg = LapMessage()
    lap_msg.timestamp = end_timestamp
    lap_msg.start_time = start_timestamp
    lap_msg.total_elapsed_time = total_time
    lap_msg.total_timer_time = total_time
    lap_msg.avg_heart_rate = avg_heart_rate
    lap_msg.min_heart_rate = min_heart_rate
    lap_msg.max_heart_rate = max_heart_rate
    if is_gpx_activity:
        lap_msg.start_position_lat = record_messages[0].position_lat
        lap_msg.start_position_long = record_messages[0].position_long
        lap_msg.end_position_lat = record_messages[-1].position_lat
        lap_msg.end_position_long = record_messages[-1].position_long
        lap_msg.min_altitude = min_altitude
        lap_msg.max_altitude = max_altitude
        lap_msg.avg_altitude = avg_altitude

    session_msg = SessionMessage()
    session_msg.message_index = 1
    session_msg.sport = sport
    if subsport:
        session_msg.sub_sport = subsport
    session_msg.timestamp = start_timestamp
    session_msg.start_time = start_timestamp
    session_msg.total_elapsed_time = total_time
    session_msg.total_timer_time = total_time
    session_msg.avg_heart_rate = avg_heart_rate
    session_msg.min_heart_rate = min_heart_rate
    session_msg.max_heart_rate = max_heart_rate
    if is_gpx_activity:
        session_msg.start_position_lat = record_messages[0].position_lat
        session_msg.start_position_long = record_messages[0].position_long
        session_msg.avg_altitude = avg_altitude
        session_msg.min_altitude = min_altitude
        session_msg.max_altitude = max_altitude

    activity_msg = ActivityMessage()
    activity_msg.timestamp = start_timestamp
    activity_msg.total_timer_time = total_time
    activity_msg.num_sessions = 1
    activity_msg.type = activity_type
    activity_msg.local_timestamp = start_timestamp / 1000

    messages = [
        file_id_msg,
        # device_info_msg,
        event_timer_start_msg,
        *record_messages,
        event_timer_stop_msg,
        lap_msg,
        session_msg,
        activity_msg,
    ]

    builder = FitFileBuilder()
    builder.add_all(messages)
    fit_file = builder.build()
    filename = os.path.join(OUTPUT_DIRECTORY, filename)
    fit_file.to_file(filename)
    assert_fit_integrity(filename)
    print(f"* Generated valid file {filename}")


main(sys.argv[1])
