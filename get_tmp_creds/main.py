import os
import json
import subprocess
import boto3
from botocore.config import Config
import click
import logging
from configparser import ConfigParser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def is_sourced():
    return os.getenv('__IS_SOURCED__') == '1'

def list_profiles():
    config_file = os.path.expanduser("~/.aws/config")
    if not os.path.exists(config_file):
        logging.error("AWS config file not found.")
        return

    with open(config_file, 'r') as f:
        lines = f.readlines()

    profiles = [line.split()[1][:-1] for line in lines if line.startswith('[profile')]
    logging.info("The following are configured profiles in ~/.aws/config:")
    for profile in profiles:
        logging.info(profile)

def get_sso_config(profile_name):
    try:
        sso_account_id = subprocess.check_output(['aws', 'configure', 'get', 'sso_account_id', '--profile', profile_name]).decode().strip()
        sso_role_name = subprocess.check_output(['aws', 'configure', 'get', 'sso_role_name', '--profile', profile_name]).decode().strip()
        sso_region = subprocess.check_output(['aws', 'configure', 'get', 'sso_region', '--profile', profile_name]).decode().strip()
        return {
            'sso_account_id': sso_account_id,
            'sso_role_name': sso_role_name,
            'sso_region': sso_region
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get SSO configuration: {e}")
        raise

def check_default_section():
    credentials_file = os.path.expanduser("~/.aws/credentials")
    if not os.path.exists(credentials_file):
        return False

    config = ConfigParser()
    config.read(credentials_file)
    return config.has_section('default') and config['default'].get('aws_access_key_id') and config['default'].get('aws_secret_access_key')

def write_credentials(profile_name, credentials, set_default):
    credentials_file = os.path.expanduser("~/.aws/credentials")
    config = ConfigParser()
    config.read(credentials_file)
    
    # Write credentials under the given profile name
    config[profile_name] = {
        'aws_access_key_id': credentials['accessKeyId'],
        'aws_secret_access_key': credentials['secretAccessKey'],
        'aws_session_token': credentials['sessionToken'],
    }
    
    # Write credentials to the 'default' profile if required
    if set_default or not check_default_section():
        config['default'] = config[profile_name]
    
    with open(credentials_file, 'w') as f:
        config.write(f)
    
    os.chmod(credentials_file, 0o600)
    logging.info(f"Credentials saved under profile '{profile_name}' in ~/.aws/credentials")

def get_aws_credentials(profile_name, set_default):
    # Clear SSO cache
    logging.info("Clearing SSO cache...")
    sso_cache_dir = os.path.expanduser('~/.aws/sso/cache')
    
    if os.path.exists(sso_cache_dir):
        cache_files = os.listdir(sso_cache_dir)
        if cache_files:
            for cache_file in cache_files:
                try:
                    os.remove(os.path.join(sso_cache_dir, cache_file))
                    logging.info(f"Removed SSO cache file: {cache_file}")
                except Exception as e:
                    logging.error(f"Failed to remove SSO cache file {cache_file}: {e}")
        else:
            logging.info("No SSO cache files to remove.")
    else:
        logging.warning("SSO cache directory does not exist.")
    
    os.environ['AWS_PROFILE'] = profile_name
    
    # Log in to AWS SSO
    logging.info(f"Logging in to AWS SSO with profile '{profile_name}'...")
    try:
        subprocess.run(['aws', 'sso', 'login', '--profile', profile_name], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to log in to AWS SSO: {e}")
        return
    
    # Get access token from the SSO cache
    sso_cache_files = [os.path.join(sso_cache_dir, f) for f in os.listdir(sso_cache_dir) if f.endswith('.json')]
    if not sso_cache_files:
        logging.error("No SSO cache files found. Please login first.")
        return

    try:
        with open(sso_cache_files[0], 'r') as f:
            access_token = json.load(f).get('accessToken')
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Failed to read or parse the SSO cache file: {e}")
        return

    if not access_token:
        logging.error("Failed to retrieve the access token from the SSO cache file.")
        return

    # Get SSO config
    logging.info("Retrieving SSO configuration...")
    sso_config = get_sso_config(profile_name)
    
    # Create an SSO client
    logging.info("Creating SSO client...")
    sso_region = sso_config['sso_region']

    client_config = Config(
        region_name=sso_region,
        signature_version='v4',
        retries={
            'max_attempts': 10,
            'mode': 'standard'
        }
    )
    sso_client = boto3.client('sso', config=client_config)
    
    # Retrieve AWS credentials
    try:
        logging.info("Retrieving AWS credentials...")
        response = sso_client.get_role_credentials(
            accountId=sso_config['sso_account_id'],
            roleName=sso_config['sso_role_name'],
            accessToken=access_token
        )
        credentials = response['roleCredentials']
    except sso_client.exceptions.UnauthorizedException as e:
        logging.error(f"Authorization error: {str(e)}")
        logging.error("Please re-authenticate with AWS SSO.")
        return

    # Write credentials to the credentials file
    write_credentials(profile_name, credentials, set_default)
    
    logging.info("All done! Try a command like 'aws s3 ls' to see if everything worked.")

@click.command()
@click.argument('profile_name', required=True)
@click.option('--list', 'list_profiles_flag', is_flag=True, help="List all profiles in ~/.aws/config")
@click.option('--set-default', is_flag=True, help="Set the retrieved credentials as the default profile in ~/.aws/credentials")
def main(profile_name, list_profiles_flag, set_default):
    if list_profiles_flag:
        list_profiles()
        return

    try:
        get_aws_credentials(profile_name, set_default)
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")

if __name__ == '__main__':
    main()
