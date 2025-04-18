# This module is dedicated to logging Customer Data
import boto3, botocore
import csv
import os


def create_s3_client_session():
    """
    Creates an AWS S3 client session using default credentials and configurations.

    Returns:
    - s3_client_session: An AWS S3 client session object configured with default credentials,
    region name, and default bucket and object key as it's always the same.

    Notes:
    - Does not require explicit environment variables for AWS credentials. Lambda Instance has s3 executable permissions.
    - Sets the default AWS region to 'us-east-2'.
    - Configures the default S3 bucket name and object key for subsequent operations.
    """
    # Create session with default configurations
    session = boto3.Session(region_name='us-east-2')
    
    # Add session config to an S3 client
    s3_client_session = session.client('s3')
    BUCKET_NAME = "shipstation-customer-data"
    s3_client_session.bucket_name = BUCKET_NAME
    
    return s3_client_session




def parse_customer_data(order):
    """
    Parses customer data from an Order object into a dictionary.

    Parameters:
    - order: An Order object containing customer data.

    Returns:
    - customer_dict: A dictionary containing parsed customer data with columns:
        'Customer ID', 'Order Source', 'Store Name', 'Shipstation', 'Order Date', 'Order Number',
        'Amount Paid', 'Customer Name', 'Street1', 'Street2', 'City', 'State', 'Country', 'Zip',
        'Phone', 'Email'.

    Notes:
    - The 'Store Name' column is currently empty and requires a function to decode store IDs into names.
    """
    def get_store_name(storeId):
        store_mapping = {
            165397 : "Nuveau Amazon",
            399784 : "Lentics Amazon",
            399912 : "Gift Haven Amazon",
            399729 : "3D Art Co Etsy",
            165604 : "Nuveau Etsy"
        }

        store_name = store_mapping.get(storeId, '')
        return store_name

    customer_data = {
        "Customer ID"  : order.Customer.id,
        "Order Source" : order.order_source,
        "Store Name"   : get_store_name(order.order_storeId),
        "Shipstation"  : order.store_name,
        "Order Date"   : order.order_date,
        "Order Number" : order.order_number,
        "Amount Paid"  : order.amount_paid,
        "Customer Name": order.Customer.name,
        "Street1"      : order.Customer.address1,
        "Street2"      : order.Customer.address2,
        "City"         : order.Customer.city,
        "State"        : order.Customer.state,
        "Country"      : order.Customer.country,
        "Zip"          : order.Customer.postal_code,
        "Phone"        : order.Customer.phone,
        "Email"        : order.Customer.email
    }

    customer_data_row = customer_data

    return customer_data_row



def get_object_name(s3_client):

    # Bucket name is set default for s3_client
    response = s3_client.list_objects_v2(Bucket=s3_client.bucket_name)

    # Check if the object exists in the bucket
    if 'Contents' in response:
        # The desired CSV is always the only object in the bucket
        for obj in response['Contents']:
            object_key = obj['Key']
            return object_key

    # Object not found in the bucket
    return False




# Get CSV from s3 bucket
def fetch_csv_from_s3():
    """
    Fetches a CSV file from an S3 bucket and saves it locally.

    Parameters:
    - s3_client: An instance of the boto3 S3 client.

    Returns:
    - csv_path (str): The file path where the CSV file is saved locally.

    Raises:
    - FileNotFoundError: If the specified local directory for saving the CSV file does not exist.
    - botocore.exceptions.ClientError: If there is an error while downloading the file from S3.
    - Exception: Catches any other unexpected exceptions.
    """
    s3_client = create_s3_client_session()
    # Use the same filename as the current s3_object
    object_key = get_object_name(s3_client)
    if not object_key:
        raise RuntimeError("Could Not Log Customer Data onto S3, failure to get s3_object_name")
    
    csv_filename = object_key
    try:
        csv_path = f'/tmp/{csv_filename}'  # Local file path to save the CSV file
        s3_client.download_file(s3_client.bucket_name, object_key, csv_path)

        return csv_path, s3_client
    
    except FileNotFoundError:
        print("Error: Local directory for saving the CSV file does not exist.")
    except botocore.exceptions.ClientError as e:
        print(f"Error downloading CSV file from S3: {e}")
    except Exception as ex:
        print(f"An unexpected error occurred: {ex}")




# write customer data into CSV
def write_customer_data(csv_file_path, customer_data_log):
    """
    Writes customer data from a list of dictionaries into a CSV file.

    Parameters:
    - csv_file_path (str): The file path to the CSV file.
    - customer_data_log (list): The list of dictionaries containing customer data to be written.

    Returns:
    - None

    Raises:
    - FileNotFoundError: If the specified CSV file does not exist.
    - PermissionError: If there are permission issues while writing to the file.
    - Exception: Catches any other unexpected exceptions.

    This function appends the data from the DataFrame `customer_df` to the CSV file located at `csv_file_path`.
    It uses the 'a' mode to append data without overwriting existing content.
    """
    try:
        with open(csv_file_path, mode="a", newline="") as file:
            for customer_data in customer_data_log:
                csv_writer = csv.DictWriter(file, fieldnames=customer_data.keys())
                csv_writer.writerow(customer_data)

    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
    except PermissionError:
        print(f"Error: Permission denied to write to '{csv_file_path}'.")
    except Exception as e:
        print(f"Error occurred: {e}")






# Update csv in s3 with new data
def upload_csv_to_s3(csv_file_path, s3_client):
    """
    Uploads a CSV file to an AWS S3 bucket using the specified S3 client.

    Parameters:
    - csv_file_path (str): The local file path of the CSV file to upload.
    - s3_client (boto3.client): An initialized AWS S3 client object incuding session configs.

    Returns:
    - None

    Raises:
    - Exception: If there is an error during the upload process.

    Notes:
    - The CSV file will be uploaded to the S3 bucket specified in the s3_client object's configuration.
    - Uses binary mode ('rb') to open the file for uploading.
    - Prints "Upload successful!" if the upload is successful.
    - Prints an error message if there is an exception during the upload process.
    """
    object_key = os.path.basename(csv_file_path)
    try:
        response = s3_client.put_object(
            Body=open(csv_file_path, 'rb'),
            Bucket=s3_client.bucket_name,
            Key=object_key
        )

        return True

    except Exception as e:
        print(f"Error uploading file: {e}")




def log_customer_data(customer_data_log):

    customer_data_csv_path, s3_client = fetch_csv_from_s3()

    write_customer_data(customer_data_csv_path, customer_data_log)

    successful = upload_csv_to_s3(customer_data_csv_path, s3_client)
    if successful:
        print("[+] Uploaded Customer Log to S3!")
        # No need to keep csv in local files
        os.remove(customer_data_csv_path)
        return True
    else:
        os.remove(customer_data_csv_path)
        return False




if __name__ == "__main__":
    print("[X] This Module is not meant to be run directly!")