from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-jenkins",
    version="1.0.0",
    description="CLI harness for Jenkins CI/CD",
    long_description="CLI-Anything harness providing Jenkins operations for agents",
    long_description_content_type="text/markdown",
    url="https://github.com/HKUDS/CLI-Anything",
    author="cli-anything contributors",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.28.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-jenkins=cli_anything.jenkins.jenkins_cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
