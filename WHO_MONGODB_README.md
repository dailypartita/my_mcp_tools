# WHO COVID-19 MongoDB Setup

This package provides scripts to collect WHO COVID-19 data and store it in MongoDB time series collections.

## Collections

The following time series collections will be created:

1. `WHO_lastweek_positivity_world` - Latest global COVID-19 positivity rates
2. `WHO_lastweek_positivity_countries` - Latest country-level COVID-19 positivity rates
3. `WHO_last28d_variants_prevalence` - Latest variant prevalence data (28-day)
4. `GISAID_last28d_variants_submitted` - Latest GISAID submission data (28-day)
5. `WHO_history_variants_prevalence` - Historical variant prevalence data
6. `WHO_history_positivity_world` - Historical global COVID-19 positivity rates

## Prerequisites

- Python 3.6+
- MongoDB (running service)
- Python packages: `pymongo`

## Usage

### Automatic Setup (Recommended)

Run the setup script which will check if MongoDB is running and set up the collections:

```bash
./setup_who_mongodb.sh
```

### Manual Setup

If you prefer to run the Python script directly:

```bash
python mongodb_setup.py
```

### Querying the Data

Use the provided query script to get data from MongoDB:

```bash
# List all collections
python query_who_data.py list

# Get latest data from a specific collection
python query_who_data.py latest WHO_lastweek_positivity_world

# Get variant prevalence data (defaults to last 28 days)
python query_who_data.py variants
python query_who_data.py variants --days 14  # Specify days

# Get countries with highest positivity rates
python query_who_data.py countries
python query_who_data.py countries --limit 5  # Limit results
python query_who_data.py countries --ascending  # Get lowest rates

# Get historical positivity rate data for the world
python query_who_data.py positivity-history
python query_who_data.py positivity-history --limit 20  # Show more weeks
```

## Custom MongoDB Connection

By default, the script connects to MongoDB at `mongodb://localhost:27017/`. 

To use a different MongoDB connection:

1. Open `mongodb_setup.py`
2. Change the connection string:
   ```python
   client = MongoClient('your_connection_string_here', serverSelectionTimeoutMS=5000)
   ```

## Troubleshooting

- **MongoDB Connection Error**: Make sure MongoDB is running
- **Data Retrieval Error**: Check your internet connection, as the script needs to fetch data from WHO

## Data Structure

Each collection uses the `date` field as the time field for the time series. Collections that track variants use the `variant` field as the meta field. 