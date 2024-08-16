import os
import json
import subprocess
import boto3
import click
import logging

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

def get_aws_credentials(profile_name, no_save):
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
    sso_client = boto3.client('sso', region_name=sso_region)
    
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

    file_permissions = 0o600

    # Set the AWS credentials as environment variables
    environment_file = os.path.expanduser("~/.aws/tmp-creds.sh")
    
    with open(environment_file, 'w') as env_file:
        logging.info("Setting AWS credentials as environment variables...")
        env_file.write("export AWS_ACCESS_KEY_ID={}\n".format(credentials['accessKeyId']))
        env_file.write("export AWS_SECRET_ACCESS_KEY={}\n".format(credentials['secretAccessKey']))
        env_file.write("export AWS_SESSION_TOKEN={}\n".format(credentials['sessionToken']))
        env_file.write("export AWS_PROFILE={}\n".format(profile_name))
        env_file.write("export AWS_REGION={}\n".format(sso_region))       
    os.chmod(environment_file, file_permissions)        
    logging.info(f"Environment Variable File Written. Use command below to source variables if you wish to: (optional)\n\nsource {environment_file}\n\n")

    if not no_save:
        logging.info("Saving credentials to ~/.aws/credentials...")
        credentials_file = os.path.expanduser("~/.aws/credentials")
        with open(credentials_file, 'w') as cred_file:
            cred_file.write(f"[default]\n")
            cred_file.write(f"aws_access_key_id = {credentials['accessKeyId']}\n")
            cred_file.write(f"aws_secret_access_key = {credentials['secretAccessKey']}\n")
            cred_file.write(f"aws_session_token = {credentials['sessionToken']}\n")
        os.chmod(credentials_file, file_permissions)   
    logging.info("All done! Try a command like 'aws s3 ls' to see if everything worked.")

@click.command()
@click.argument('profile_name', required=False)
@click.option('--list', 'list_profiles_flag', is_flag=True, help="List all profiles in ~/.aws/config")
@click.option('--no-save', is_flag=True, help="Do not save credentials to ~/.aws/credentials (Saved by default)")
def main(profile_name, list_profiles_flag, no_save=False):
    if list_profiles_flag:
        list_profiles()
        return

    if not profile_name:
        click.echo(main.__doc__)
        return

    try:
        get_aws_credentials(profile_name, no_save)
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")

if __name__ == '__main__':
    main()
