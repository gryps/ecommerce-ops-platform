from . import copies, jianying, materials, operations, products, source_files, tags, voice_narrations

ROUTERS = [
    operations.router,
    products.router,
    tags.router,
    source_files.router,
    materials.router,
    copies.router,
    voice_narrations.router,
    jianying.router,
]
