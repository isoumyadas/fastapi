from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.db import Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit
import shutil
import os
import uuid
import tempfile

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

# The above function will be automatically run, as soon as app is started and create the database in the tables for us
app = FastAPI(lifespan=lifespan)

from text_posts import text_posts
from app.schemas import PostCreate

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    session: AsyncSession = Depends(get_async_session)
):
    
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        upload_result = imagekit.files.upload(
            file=open(temp_file_path, "rb"),
            file_name=file.filename,
            folder="/feeds",
            tags=["feed", "featured"]
        )
# If something breaks here, you shoudld also remove the uploadded image in imagekitio. 

        if upload_result.file_id:
            post = Post(
                    caption = caption,
                    url=upload_result.url,
                    file_type="video" if file.content_type.startswith("video/") else "image",
                    file_name=upload_result.name
                )

            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()


@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session)
): 
    # This is how we execute the query.
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))

    # for all the post
    """
    result = await session.execute(select(Post))
    """

    posts = [row[0] for row in result.all()]

    posts_data = []

    for post in posts:
        posts_data.append({
            "id": str(post.id),
            "caption" : post.caption,
            "url" : post.url,
            "file_type" : post.file_type,
            "file_name" : post.file_name,
            "created_at" : post.created_at.isoformat()
        })
    
    return {"posts" : posts_data}

@app.delete("/post/{post_id}")
async def delete_post(post_id: str, session: AsyncSession = Depends(get_async_session)):
    try:
        post_uuid = uuid.UUID(post_id)

        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        await session.delete(post)
        await session.commit()
        
        return {"success" : True, "message" : "Post deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# * You can add the functionality to remove the image from the imagekit when you delete particular post.
# * Same way you shouldn't be upload the image to imagekit if something breaks.



# ============================= DEMO ========================================


# @app.get("/posts")
# def get_all_posts(limit : int = None):
#     if limit:
#         return list(text_posts.values())[:limit]
#     return text_posts

# @app.get("/posts/{id}")
# def get_post_by_id(id: int) -> PostCreate:
#     # return text_posts[id]
#     if id not in text_posts:
#         raise HTTPException(status_code=404, detail="Post not found!")
#     return text_posts.get(id)

# @app.post("/posts")
# def create_post(post: PostCreate) -> PostCreate:
#     new_post = {"title" : post.title, "content" : post.content}
#     text_posts[max(text_posts.keys()) + 1] = new_post
#     return new_post

# @app.delete("/posts/{id}")
# def delete_post_by_id(id: int) -> PostCreate:
#     if id not in text_posts:
#         raise HTTPException(status_code=404, detail="Post not found!")
    
#     removed = text_posts.pop(id)
#     return removed
