# test_app.py

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime
import json

# Assume app.py is in the same directory or accessible via PYTHONPATH
from app import app as flask_app, load_data_from_gcs, compute_today_vs_typical, compute_weekly_summary, compute_weekly_profiles

# Sample data for mocking GCS
SAMPLE_JSONL = """
{"timestamp": "2025-10-13T10:05:00", "count": 10}
{"timestamp": "2025-10-13T10:15:00", "count": 12}
{"timestamp": "2025-10-06T10:08:00", "count": 8}
{"timestamp": "2025-10-13T18:30:00", "count": 50}
{"timestamp": "2025-10-12T11:00:00", "count": 20}
{"timestamp": "2025-10-13T09:59:00", "count": 5}
{"timestamp": "2025-10-13T10:01:00", "count": 9}
"""

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    flask_app.config.update({
        "TESTING": True,
    })
    yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

# 1. Test load_data_from_gcs
@patch('app.storage.Client')
def test_load_data_from_gcs(mock_storage_client):
    """
    Tests the load_data_from_gcs function.
    Mocks Google Cloud Storage to return sample JSONL data.
    Verifies that the function returns a DataFrame with the correct columns,
    data types, and that timestamps are correctly floored and timezone-aware.
    """
    # Mock GCS client, bucket, and blob
    mock_blob = MagicMock()
    mock_blob.download_as_bytes.return_value = SAMPLE_JSONL.encode('utf-8')
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage_client.return_value.bucket.return_value = mock_bucket

    # Call the function
    df = load_data_from_gcs()

    # Assertions
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert 'timestamp' in df.columns
    assert 'attendance_count' in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df['timestamp'])
    assert df['timestamp'].dt.tz is not None
    
    # Check that timestamp is floored to 10 minutes
    assert all(df['timestamp'].dt.second == 0)
    assert all(df['timestamp'].dt.minute % 10 == 0)


# 2. Test compute_today_vs_typical
@patch('app.pd.Timestamp.now')
def test_compute_today_vs_typical(mock_pd_timestamp_now):
    """
    Tests the compute_today_vs_typical function.
    Mocks datetime.now() to a fixed date.
    Verifies that it correctly calculates 'today's data and the 'typical'
    average for the same weekday over the last 4 weeks.
    """
    mock_pd_timestamp_now.return_value = pd.Timestamp('2025-10-13 12:00:00', tz='Europe/Zurich')  # A Monday

    data = {
        'timestamp': pd.to_datetime([
            '2025-10-13 10:00:00',  # Today, Monday, count 10
            '2025-10-13 10:10:00',  # Today, Monday, count 20
            '2025-10-06 10:00:00',  # Last week, Monday, count 8
            '2025-09-29 10:00:00',  # 2 weeks ago, Monday, count 6
            '2025-10-12 10:00:00',  # Sunday, count 15
        ]).tz_localize('Europe/Zurich'),
        'attendance_count': [10, 20, 8, 6, 15]
    }
    df = pd.DataFrame(data)

    data_today, data_avg = compute_today_vs_typical(df.copy())

    # Assert today's data is correct
    assert len(data_today) == 2

    # Assert average data is correct for Monday
    assert len(data_avg) == 2
    avg_10_00 = data_avg[data_avg["time"] == "10:00"]
    avg_10_10 = data_avg[data_avg["time"] == "10:10"]
    
    assert avg_10_00['attendance_count'].iloc[0] == pytest.approx((10 + 8 + 6) / 3)
    assert avg_10_10['attendance_count'].iloc[0] == pytest.approx(20)


# 3. Test compute_weekly_summary
@patch('app.pd.Timestamp.now')
def test_compute_weekly_summary(mock_pd_timestamp_now):
    """
    Tests the compute_weekly_summary function.
    Verifies that it correctly computes the average attendance for defined
    time buckets and finds the peak attendance for each weekday.
    """
    mock_pd_timestamp_now.return_value = pd.Timestamp('2025-10-15 12:00:00', tz='Europe/Zurich') # A Wednesday
    data = {
        'timestamp': pd.to_datetime([
            '2025-10-13 07:30:00',  # Monday, count 10
            '2025-10-13 07:40:00',  # Monday, count 20
            '2025-10-14 18:00:00',  # Tuesday, count 100 (peak)
            '2025-10-14 19:10:00',  # Tuesday, count 50
        ]).tz_localize('Europe/Zurich'),
        'attendance_count': [10, 20, 100, 50]
    }
    df = pd.DataFrame(data)

    summary, peaks = compute_weekly_summary(df.copy())

    # Test summary pivot table
    assert not summary.empty
    mon_summary = summary[summary['weekday_name'] == 'Monday']
    mon_summary = mon_summary.dropna()
    assert mon_summary.iloc[0]['time_slot'] == '07:00'
    assert mon_summary.iloc[0]['attendance_count'] == 15

    # Test peaks
    assert not peaks.empty
    assert len(peaks) == 2  # One peak for Monday, one for Tuesday
    tue_peak = peaks[peaks['weekday_name'] == 'Tuesday'].iloc[0]
    assert tue_peak['peak_count'] == 100
    assert tue_peak['peak_time'] == pd.to_datetime('2025-10-14 18:00:00').tz_localize('Europe/Zurich')


# 4. Test compute_weekly_profiles
def test_compute_weekly_profiles():
    """
    Tests the compute_weekly_profiles function.
    Verifies that it correctly groups by weekday and time, and calculates
    the mean 'visitors' count.
    """
    data = {
        'timestamp': pd.to_datetime([
            '2025-10-13 10:00:00',  # Monday, count 10
            '2025-10-13 10:00:00',  # Monday, count 20
            '2025-10-14 11:00:00',  # Tuesday, count 30
        ]).tz_localize('Europe/Zurich'),
        'attendance_count': [10, 20, 30]
    }
    df = pd.DataFrame(data)
    
    profiles = compute_weekly_profiles(df.copy())
    
    assert not profiles.empty
    assert 'visitors' in profiles.columns  # Check for renamed column
    
    mon_profile = profiles[profiles['weekday'] == 'Monday']
    assert mon_profile.iloc[0]['time'] == '10:00'
    assert mon_profile.iloc[0]['visitors'] == 15  # (10+20)/2

# 5. Test Flask route with Plotly charts
@patch('app.pd.Timestamp.now')
@patch('app.load_data_from_gcs')
def test_index_route_with_plotly(mock_load_data, mock_pd_timestamp_now, client):
    """
    Tests the main Flask route '/' with Plotly charts.
    Mocks the data loading function and checks for Plotly JSON in the response.
    """
    mock_pd_timestamp_now.return_value = pd.Timestamp('2025-10-13 12:00:00', tz='Europe/Zurich')
    # Create a sample dataframe for the mock to return
    data = {
        'timestamp': pd.to_datetime(['2025-10-13 10:00:00', '2025-10-13 10:10:00']).tz_localize('Europe/Zurich'),
        'attendance_count': [10, 20]
    }
    sample_df = pd.DataFrame(data)
    mock_load_data.return_value = sample_df

    response = client.get('/')
    
    assert response.status_code == 200
    assert b'Fitnesspark Attendance Dashboard' in response.data
    assert b'Today vs. Typical Attendance' in response.data
    assert b'Weekly Attendance Patterns' in response.data
    assert b'Weekly Summary and Peak Times' in response.data
    assert b'All-Time Attendance' in response.data
