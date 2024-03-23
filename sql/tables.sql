drop table if exists products_emb;
CREATE TABLE products_emb (
    Id integer,
    gender VARCHAR(50),
    masterCategory VARCHAR(100),
    subCategory VARCHAR(100),
    articleType VARCHAR(100),
    baseColour VARCHAR(50),
    Season text,
    year INTEGER,
    usage text null,
    productDisplayName TEXT null,
    Image_path text null, 
    embedding vector(512)
);

drop table if exists products;
CREATE TABLE products(
    Id integer,
    gender VARCHAR(50),
    masterCategory VARCHAR(100),
    subCategory VARCHAR(100),
    articleType VARCHAR(100),
    baseColour VARCHAR(50),
    Season text,
    year INTEGER,
    usage text null,
    productDisplayName TEXT null
);
