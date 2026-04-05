import os
import requests
from datetime import datetime
from .gtfs_ingest import GTFS_PATH

def download_latest_gtfs_if_needed():
    # The dataset ID or name from the URL provided
    dataset_id = "horarios-paragens-e-rotas-em-formato-gtfs-stcp"
    base_url = "https://opendata.porto.digital/api/3/action/package_show"

    print(f"Fetching metadata for dataset: {dataset_id}...")

    try:
        # 1. Get dataset metadata from CKAN API
        response = requests.get(base_url, params={'id': dataset_id})
        response.raise_for_status()
        data = response.json()

        if not data.get('success'):
            print("Error: API request was not successful.")
            return False

        # 2. Filter resources that are GTFS files (usually .zip)
        resources = data['result']['resources']
        gtfs_resources = [
            res for res in resources
            if res['format'].lower() == 'gtfs' or res['url'].endswith('.zip')
        ]

        if not gtfs_resources:
            print("No GTFS resources found in this dataset.")
            return False

        # 3. Identify the most recent file based on the 'created' or 'metadata_modified' field
        # We sort by 'created' timestamp in descending order
        latest_res = max(gtfs_resources, key=lambda x: x.get('created', ''))

        file_url = latest_res['url']
        file_name = latest_res.get('name', 'gtfs_stcp.zip')
        if not file_name.endswith('.zip'):
            file_name += ".zip"

        print(f"Found latest file: {file_name}")
        print(f"Upload date: {latest_res.get('created')}")

        # Check if we already have this file downloaded
        if os.path.exists(os.path.join(GTFS_PATH, "package_downloads", file_name)):
            print(f"File {file_name} already exists.")
            return False
        else:
            print(f"Downloading from: {file_url} ...")

            # 4. Download the file
            with requests.get(file_url, stream=True) as r:
                r.raise_for_status()
                new_gtfs_filepath_ = os.path.join(GTFS_PATH, "package_downloads", file_name)
                with open(new_gtfs_filepath_, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            print(f"Success! Saved as {file_name}")
            return new_gtfs_filepath_

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")


def archive_previous_gtfs():
    current_date_str = datetime.now().strftime("%Y%m%d")  # Current date in AAAAMMDD format
    
    # Create a new subdirectory inside the archive folder with the current date
    archive_subdir = os.path.join(GTFS_PATH, "archive", f"up to {current_date_str}")
    os.makedirs(archive_subdir, exist_ok=True)

    gtfs_files_archived = []
    gtfs_files_to_be_archived = [f for f in os.listdir(GTFS_PATH) if f.endswith(".txt")]
    for file in gtfs_files_to_be_archived:
        # Move the file to the new subdirectory
        os.rename(os.path.join(GTFS_PATH, file), os.path.join(archive_subdir, file))
        gtfs_files_archived.append(file)

    print(f"Archived the following {len(gtfs_files_to_be_archived)} GTFS files to {archive_subdir}:")
    for file in gtfs_files_archived:
        print(f"- {file}")

    return gtfs_files_archived
    # returns the list of archived files for comparison with new GTFS file list

def extract_new_gtfs_from_zip(zip_file_path):
    import zipfile

    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(GTFS_PATH)
    print(f"Extracted GTFS files from {zip_file_path} to {GTFS_PATH}")

    gtfs_files_extracted = [f for f in os.listdir(GTFS_PATH) if f.endswith(".txt")]

    return gtfs_files_extracted
    # returns the list of extracted files for comparison with old GTFS file list


def main():
    new_gtfs_filepath = download_latest_gtfs_if_needed()
    if new_gtfs_filepath:
        print("New GTFS file downloaded. Archiving the previous version...")
        old_gtfs_files = archive_previous_gtfs()
        new_gtfs_files = extract_new_gtfs_from_zip(new_gtfs_filepath)

        print("\nComparing old and new GTFS file lists...")
        files_missing_in_new = [f for f in old_gtfs_files if f not in new_gtfs_files]
        print(f"Files present in old GTFS but missing in new GTFS: \n{files_missing_in_new}")

        print("\nGTFS update process completed.")

        return True
    else:
        print("No new GTFS file was downloaded. No update needed.")
        return False

if __name__ == "__main__":
    main()