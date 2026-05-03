from setuptools import setup

setup(
    name="lettuce",
    version="0.1.0",
    description="An agent-operated markdown+git protocol for reviewable operating context.",
    license="MIT",
    python_requires=">=3.9",
    packages=["lettuce"],
    package_data={"lettuce": ["prompts/*.md", "schemas/*.json", "runtime_seed.json"]},
    entry_points={"console_scripts": ["lettuce=lettuce.cli:main"]},
)
