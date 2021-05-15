import setuptools

with open("README.md", "r") as fh:
	long_description = fh.read()

setuptools.setup(
	name="bitvavo-aio",
	version="1.0.2",
	author="@cyberjunky",
	author_email="ron@cyberjunky.nl",
	description="Bitvavo asynchronous Python client",
	license="MIT",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/cyberjunky/bitvavo-aio",
	packages=setuptools.find_packages(),
	classifiers=[
		"Development Status :: 4 - Beta",
		"Framework :: AsyncIO",
		"Intended Audience :: Developers",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3.6",
		"Programming Language :: Python :: 3.7",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
		"Topic :: Software Development :: Libraries",
		"Topic :: Software Development :: Libraries :: Python Modules",
		"Typing :: Typed",
	],
	install_requires=[
		'aiohttp>=3.7.4,<4',
	],
	python_requires='>=3.6',
)
