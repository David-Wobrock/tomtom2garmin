# TomTom Sports Watch files to Garmin FIT files

End of August, I received a heartbreaking email:

> End of September, the TomTom Sports mobile app, Sports website, and Sports Connect desktop application will be discontinued and permanently removed. 

I won't be able to leverage my sports watch in a month from now.

Therefore, I got a Garmin watch, but I obviously didn't want to lose my over 800 activities I accumulated over the years.
And those weren't transferred to Strava or whatever platform.

I could only **download hundreds .gpx and .json_2 files from the TomTom website.**
And the challenge: **importing them back into Garmin, without information loss**.

➡️ **This project converts TomTom Sports .gpx and .json_2 files into .fit files** that Garmin understands and can import.

# Usage

Used with Python 3.10.

1. Install dependencies
```
pip install requirements.txt
```
(in a virtual environment, or not - as you wish)


2. Download the `tomtom2garmin.py` file

3. Run the script on your TomTom files

```
python tomtom2garmin.py tomtomActivities/
```

4. Wait for it to generate all `.fit` files in `output/`

5. Upload them into Garmin Connect

https://connect.garmin.com/modern/import-data

To avoid overloading the UI, I imported 100 files by 100 files.

# Supported activities

For now, the script only handles the activities I used to do:
- Running (gpx)
- Cycling (gpx)
- Hiking (gpx)
- Treadmill (json_2)
- Indoor cycling (json_2)
- Gym (json_2)

The script ignores tracking files, which are just the daily steps counter from my understanding.

# Why this project?

TomTom Sports exports gpx files when GPS data is used for the activity (latitude, longitude, elevation - additionally to the heartrate).
But it exports quite custom json_2 files (which are the same as json files) for activities without geolocation.

Issues are that:
- when importing TomTom GPX files into Garmin, the activity type is not recognized. You don't know if the activity was a run, a hike or biking.
- Garmin has no idea how to import the json_2 files.

# Reference

The biggest enabler is https://pypi.org/project/fit-tool/ & https://bitbucket.org/stagescycling/python_fit_tool/src/main/
which allows writing FIT files using Python.

FIT specification: https://developer.garmin.com/fit/overview/