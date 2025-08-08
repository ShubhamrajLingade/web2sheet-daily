# UAE Property Data Scraper & Sheet Uploader

This project automates the daily scraping of property listings in the UAE (primarily Dubai) that were posted in the last 24 hours, and uploads the data to Google Sheets for analysis and tracking. It also includes functionality to compare scraped listings with sales data from 1,777 Dubai real estate properties.

Key Features:

Daily Property Scraping:
Scrapes newly listed properties (last 24 hours) from target real estate websites.

Google Sheet Integration:
Creates a new Google Sheet every day, and uploads the scraped data.

Structured Sub-Sheets:
Each daily sheet includes 8 sub-sheets to categorize and filter data based on custom criteria.

Sales Data Comparison:
Automatically compares scraped listings to recent sales data from Dubai properties.

Massive Sales Dataset:
Integrates with a large .xlsx file containing sales data from 1,777 Dubai real estate developments.

Sheet Mapping & Matching:
Uses apartment names to match and map relevant sales data to the listings.
Uploads matched sales insights to the appropriate sub-sheet for reference.

Sheet ID Management:
Uploads large .xlsx files in parts and stores sheet IDs separately for organized tracking and access.

How It Works (Daily Process):

Scrape new property listings from the past 24 hours.

Create a new Google Sheet for the day.

Generate 8 categorized sub-sheets inside the main sheet.

Upload scraped data into these sub-sheets based on filters.

Load the large .xlsx file containing sales data from 1,777 properties.

Match each property to its latest sales data by apartment name.

Upload the matched sales data into the daily sheet for comparison.

Repeat the entire process daily via a scheduled job (e.g., using cron or cloud functions).
