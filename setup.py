import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="discord_bot_maker",
    version="0.0.5",
    author="Aaryan Dehade",
    author_email="dehadeaaryan@gmail.com",
    description="A Python Package to make Discord bots with ease. (It also has a lot of documentation so you will never be stuck)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dehadeaaryan/discord-bot-maker",
    project_urls={
        "Bug Tracker": "https://github.com/dehadeaaryan/discord-bot-maker/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)