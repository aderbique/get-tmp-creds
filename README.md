# AWS Temporary Credentials CLI

## Overview

This Python CLI tool helps AWS users easily obtain temporary credentials using AWS SSO. It simplifies the process of logging in via SSO, exporting credentials as environment variables, and saving them to `~/.aws/credentials`. This tool is beneficial for developers and DevOps engineers who frequently switch between AWS roles or need temporary credentials for various tasks.

## Target Audience

- **Developers**: Quickly switch AWS roles and access temporary credentials without manually configuring environment variables.
- **DevOps Engineers**: Automate credential management in scripts or CI/CD pipelines.
- **AWS Administrators**: Simplify the process of accessing and managing temporary credentials.

## Features

- **List Configured Profiles**: View all AWS profiles configured in `~/.aws/config`.
- **Login and Fetch Credentials**: Log in to AWS SSO, retrieve temporary credentials, and set environment variables.
- **Save Credentials**: Optionally save credentials to `~/.aws/credentials` for persistent use under the specified profile.
- **Profile-based Configuration**: Allows credentials to be saved under the profile specified in the CLI argument.
- **Conditional Default Profile Handling**: Checks if the default profile exists and handles it based on a `--set-default` flag.
- **Logging**: Detailed logging for tracking the process and debugging issues.

## Prerequisites

Before using this script, ensure you have the following prerequisites:

1. **AWS CLI**: The script uses AWS CLI to interact with AWS services. Make sure you have installed and configured the AWS CLI with valid credentials.
2. **AWS SSO Configuration**: Ensure your `~/.aws/config` file is properly configured with the AWS account you wish to access. Refer to the example below or `config.example` in this repository.

## Installation

Ensure you have Python 3.x installed and install the required packages:

```bash
pip install get-tmp-creds
```

View all PyPi releases here: [get-tmp-creds on PyPi](https://pypi.org/project/get-tmp-creds/).

## Usage

### Listing AWS Profiles

To list all profiles configured in your `~/.aws/config` file:

```bash
get-tmp-creds --list
```

### AWS SSO Configuration Example

```ini
[default]
region = us-west-2

[profile my-dev-acct]
sso_start_url = https://mycompany.awsapps.com/start
sso_region = us-east-1
sso_account_id = 0123456789
sso_role_name = PowerUsersRole
region = us-west-2
```

### Getting Temporary Credentials

To get temporary AWS credentials for a specified profile and save them under that profile in `~/.aws/credentials`:

```bash
get-tmp-creds <profile_name>
get-tmp-creds my-dev-acct
```

This will:
1. Clear the SSO cache.
2. Log in to AWS SSO.
3. Retrieve and export temporary credentials as environment variables.
4. Save credentials to `~/.aws/credentials` under the specified profile.

### Options

- **`--list`**: Lists all configured AWS profiles.
- **`--no-save`**: Prevents saving credentials to `~/.aws/credentials`. By default, credentials are saved under the profile name.
- **`--set-default`**: If the `default` profile in `~/.aws/credentials` already exists and is non-empty, this option forces the script to overwrite it.

### Example

1. **List Profiles**

    ```bash
    get-tmp-creds --list
    ```

2. **Get and Export Credentials**

    ```bash
    get-tmp-creds my-profile
    ```

    This command logs in to AWS SSO using the `my-profile` profile, retrieves temporary credentials, and writes them to an environment variable file. You can source this file to set the credentials in your current shell session.

3. **Get Credentials without Saving**

    ```bash
    get-tmp-creds my-profile --no-save
    ```

    This command performs the same actions as the previous command but does not save the credentials to `~/.aws/credentials`.

4. **Set Default Profile**

    ```bash
    get-tmp-creds my-profile --set-default
    ```

    This command saves the credentials under the `default` profile in `~/.aws/credentials`, even if it is already populated.

## File Permissions

The script writes temporary credentials to a file named `~/.aws/tmp-creds.sh` with permissions set to `600` (read and write for the owner only). This ensures the file is secure and only accessible by the owner.

## Troubleshooting

- **UnauthorizedException**: If you encounter authorization errors, ensure that you have logged in with AWS SSO and that your access token is valid.
- **ExpiredToken**: If you see errors related to expired tokens, re-authenticate using `aws sso login` for the respective profile.

## Logging

The script uses Python’s `logging` module to provide detailed logs of its operations. Logs are output to the console and can help troubleshoot issues or verify that the script is functioning correctly.

## Contributing

Feel free to submit issues, feature requests, or pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.