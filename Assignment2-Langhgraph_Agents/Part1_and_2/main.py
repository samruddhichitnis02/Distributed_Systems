from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional

app = FastAPI(title="Book Library Management System")

# Setup templates directory
templates = Jinja2Templates(directory="templates")

# Mount static files (to serve background image)
app.mount("/static", StaticFiles(directory="templates"), name="static")

# In-memory database for books
books_db = [
    {"id": 1, "title": "The Casual Vacancy", "author": "J.K. Rowling"},
    {"id": 2, "title": "The Handmaid's Tale", "author": "Margaret Atwood"},
    {"id": 3, "title": "One Hundred Years of Solitude", "author": "Gabriel García Márquez"},
]

# Track the next ID for new books
next_id = 4


def get_next_id():
    """Get the next available ID for a new book."""
    global next_id
    current_id = next_id
    next_id += 1
    return current_id


# ============================================
# HOME PAGE - List all books with search
# ============================================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, search: Optional[str] = None):
    """
    Display the home page with all books.
    QUESTION 4: Supports search functionality by book title.
    """
    if search:
        # Filter books by title (case-insensitive search)
        filtered_books = [
            book for book in books_db 
            if search.lower() in book["title"].lower()
        ]
        return templates.TemplateResponse(
            "home.html",
            {"request": request, "books": filtered_books, "search_query": search}
        )
    
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "books": books_db, "search_query": ""}
    )


# ============================================
# QUESTION 1: ADD NEW BOOK
# ============================================
@app.get("/add", response_class=HTMLResponse)
async def add_book_form(request: Request):
    """Display the form to add a new book."""
    return templates.TemplateResponse(
        "add.html",
        {"request": request}
    )


@app.post("/add")
async def add_book(title: str = Form(...), author: str = Form(...)):
    """
    Add a new book to the database.
    After adding, redirect to home page to show updated list.
    """
    new_book = {
        "id": get_next_id(),
        "title": title,
        "author": author
    }
    books_db.append(new_book)
    return RedirectResponse(url="/", status_code=303)


# ============================================
# QUESTION 2: UPDATE BOOK
# ============================================
@app.get("/update/{book_id}", response_class=HTMLResponse)
async def update_book_form(request: Request, book_id: int):
    """Display the form to update an existing book."""
    # Find the book by ID
    book = next((b for b in books_db if b["id"] == book_id), None)
    
    if book is None:
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse(
        "update.html",
        {"request": request, "book": book}
    )


@app.post("/update/{book_id}")
async def update_book(
    book_id: int,
    title: str = Form(...),
    author: str = Form(...)
):
    # Find and update the book
    for book in books_db:
        if book["id"] == book_id:
            book["title"] = title
            book["author"] = author
            break
    
    return RedirectResponse(url="/", status_code=303)


# ============================================
# DELETE SPECIFIC BOOK
# ============================================
@app.post("/delete/{book_id}")
async def delete_book(book_id: int):
    """Delete a specific book by its ID."""
    global books_db
    books_db = [book for book in books_db if book["id"] != book_id]
    return RedirectResponse(url="/", status_code=303)


# ============================================
# QUESTION 3: DELETE BOOK WITH HIGHEST ID
# ============================================
@app.post("/delete-highest")
async def delete_highest_id():
    """
    Delete the book with the highest ID.
    After deleting, redirect to home page to show updated list.
    """
    global books_db
    
    if books_db:
        # Find the book with the highest ID
        highest_id_book = max(books_db, key=lambda x: x["id"])
        # Remove it from the list
        books_db = [book for book in books_db if book["id"] != highest_id_book["id"]]
    
    return RedirectResponse(url="/", status_code=303)


# ============================================
# Run the application
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
