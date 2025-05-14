#!/bin/bash

echo "WHO COVID-19 MongoDB Setup Script"
echo "================================="

# Check if MongoDB is running
echo "Checking if MongoDB is running..."
if command -v mongod &> /dev/null; then
    # If mongod command exists
    if pgrep -x "mongod" &> /dev/null; then
        echo "MongoDB is running."
    else
        echo "MongoDB is installed but not running."
        echo "Attempting to start MongoDB..."
        
        # Try to start MongoDB (different methods depending on system)
        if command -v systemctl &> /dev/null; then
            sudo systemctl start mongod
        elif command -v service &> /dev/null; then
            sudo service mongod start
        else
            echo "Could not automatically start MongoDB."
            echo "Please start MongoDB manually and try again."
            exit 1
        fi
        
        # Check if start was successful
        sleep 2
        if pgrep -x "mongod" &> /dev/null; then
            echo "MongoDB started successfully."
        else
            echo "Failed to start MongoDB. Please start it manually."
            exit 1
        fi
    fi
else
    echo "MongoDB does not appear to be installed."
    echo "Please install MongoDB and try again."
    exit 1
fi

# Run the Python script
echo -e "\nRunning WHO COVID-19 MongoDB setup script..."
python3 mongodb_setup.py

# Exit with the same status as the Python script
exit $? 