from setuptools import setup, find_packages

setup(
    name="django-core-app",  # Nombre que tendrá en PyPI
    version="0.1.25",         # Versión inicial (usa Semantic Versioning)
    packages=find_packages(),
    include_package_data=True,  # Incluye archivos declarados en MANIFEST.in
    install_requires=[
        "Django>=2.2",         # Dependencia esencial, puedes agregar más si las necesitas
        "bson",
        "beautifulsoup4",
        "django-allauth",
        "django-autocomplete-light",
        "django-cropperjs",
        "django-nested-admin",
        "django-mptt",
        "django-pwa",
        "django-resized",
        "django-tinymce==3.5.0",
        "django-social-share",
        "django-webpush",
        "firebase-admin",
        "numpy",
        "pandas",
        "pillow",
        "psycopg2-binary",
    ],
    author="juanbacan",
    author_email="juan.ingaor@gmail.com",
    description="Una aplicación reusable de Django para crear un proyecto base",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/tuusuario/django-core-app",  # URL del repositorio (cuando esté en GitHub)
    classifiers=[
        "Framework :: Django",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
