## Project Overview

This project combines backend application development with a structured multi-agent workflow.

It includes:

1.  A FastAPI-based Book Library Management System with dynamic CRUD operations and search functionality.
2.  A stateful agent graph implemented using LangGraph and a local LLM via Ollama.

The focus of this implementation is clean routing logic, structured state management, and controlled agent collaboration.

------------------------------------------------------------------------

# Part I -- Book Library Management System

## Application Description

The application provides a user-friendly interface for managing a collection of books.

Core capabilities include:

-   Viewing all books in a structured table
-   Adding new books through a form
-   Updating existing book details
-   Deleting specific books
-   Removing the book with the highest ID
-   Searching books by title with dynamic filtering

The frontend uses styled HTML templates rendered via Jinja2, while FastAPI handles routing and form submissions.
------------------------------------------------------------------------

## Backend Design

### In-Memory Storage

Books are stored in a Python list acting as a lightweight in-memory database. A helper function dynamically assigns unique IDs.

### CRUD Operations

Routes are defined to handle: - Creation of new records 
			      - Updating existing records 
			      - Deletion (single and highest ID) 
			      - Query-based filtering

Redirect responses ensure the UI reflects updates immediately after actions.
------------------------------------------------------------------------

## Running the Application

Install dependencies:

pip install fastapi uvicorn jinja2

Start the server:

uvicorn main:app --reload

Open in browser:

http://127.0.0.1:8000

------------------------------------------------------------------------

# Part II -- Stateful Agent Graph

## Overview

This component introduces a dynamic agent workflow using:

-   LangGraph
-   LangChain's Ollama integration
-   A locally running LLM

Instead of a fixed sequence, the workflow uses conditional routing and shared state to allow controlled revision cycles.
------------------------------------------------------------------------

## Architecture

### Shared State

A TypedDict-based state object stores:

-   Blog input
-   Planner output
-   Reviewer feedback
-   Turn counter
-   LLM instance

All nodes read from and write to this shared memory.

------------------------------------------------------------------------

### Planner Node

Responsible for generating:

-   Three topical tags
-   A concise summary

The output is parsed and normalized before being saved to state.

------------------------------------------------------------------------

### Reviewer Node

Validates:

-   Correct tag count
-   Summary length constraints
-   Basic relevance check

If issues are found, feedback is stored and the system loops back for revision.

------------------------------------------------------------------------

### Supervisor & Routing Logic

A supervisor node increments a turn counter to prevent infinite loops.

A routing function dynamically decides whether to:

-   Send control to the Planner
-   Send control to the Reviewer
-   End execution

This creates a flexible, self-correcting workflow.

------------------------------------------------------------------------

## Execution Process

1.  Initialize state with blog input and LLM.
2.  Compile the LangGraph workflow.
3.  Execute using `.stream()`.
4.  Observe node transitions and state updates.
5.  Produce final structured JSON output.

A maximum turn limit ensures safe termination.

------------------------------------------------------------------------

## Running the Agent System

Ensure Ollama is running locally with the required model.

Then execute:

python agent_demo.py

The console will display:

-   Planner output
-   Reviewer feedback
-   Node transitions
-   Final structured JSON result

------------------------------------------------------------------------

# Technical Highlights

-   FastAPI routing & templating
-   Dynamic CRUD operations
-   Conditional logic with state-driven routing
-   TypedDict-based shared memory
-   Multi-agent collaboration pattern
-   Loop-based revision mechanism
-   Structured LLM output handling

------------------------------------------------------------------------

## Conclusion

This project demonstrates how structured backend services and intelligent agent workflows can be combined using clear routing logic
and centralized state management. The result is a clean CRUD web application alongside a flexible, self-correcting AI agent graph.
