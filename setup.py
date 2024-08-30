from setuptools import setup, find_packages

setup(
    name='get-tmp-creds', 
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'click',
        'boto3',
    ],
    entry_points={
        'console_scripts': [
            'get-tmp-creds=get_tmp_creds.main:main',
        ],
    },
    include_package_data=True,
    description='A CLI tool for managing AWS SSO temporary credentials.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/aderbique/get-tmp-creds',
    author='Austin Derbique',
    author_email='austin@derbique.org',
    license='MIT',
)
