
## Project Overview

This project combines frontend web development and a small multi-agent
AI workflow.

It is divided into two main components:

1.  A Blog Submission Web Application built with HTML, CSS, and
    JavaScript.
2.  A Local LLM-based Agent Workflow built using Python and Ollama.

The goal of this project is to demonstrate practical understanding of modern JavaScript features, structured JSON handling, closures,
containerization, and agent-based AI orchestration.
------------------------------------------------------------------------

# Part I -- Blog Submission Web Application

## Description

The web application allows users to create and submit a blog post
through a responsive form interface.

Users can: - Enter a blog title - Provide author details - Select a
category - Write blog content - Agree to terms before submission

The interface is styled with custom CSS and Google Fonts to provide a clean, modern appearance.

------------------------------------------------------------------------

## JavaScript Functionality

The JavaScript logic enhances the form with the following features:

### Form Validation (Arrow Function)

-   Ensures blog content exceeds 25 characters
-   Ensures the terms checkbox is selected
-   Displays clear alert messages if validation fails

### JSON Handling

-   Converts submitted form data into a formatted JSON string
-   Logs structured output to the console

### Object Destructuring

-   Extracts specific fields (title and email) from parsed JSON

### Spread Operator

-   Adds a timestamp (`submissionDate`) to the submission object

### Closure Implementation

-   Tracks how many times the form has been successfully submitted
-   Maintains state across submissions without global variables

------------------------------------------------------------------------

# Deployment

## Docker

The application can be containerized and run locally using:
Access via: http://localhost:8080

## AWS ECS

The Docker image can be deployed to AWS ECS with a single running task. The service exposes a public IP for accessing the application
externally.
------------------------------------------------------------------------

# Part II -- Agentic AI Workflow

## Overview

This component builds a lightweight multi-agent system using:

-   Python 3.11+
-   Ollama
-   Local model: smollm:1.7b

The workflow processes a blog title and content and produces:

-   Exactly three topical tags
-   A one-sentence summary (25 words or fewer)
-   Structured JSON output

------------------------------------------------------------------------

## Agent Architecture

The system follows a three-step pipeline:

### Planner

Generates candidate tags and a summary based on the blog input.

### Reviewer

Validates constraints such as: - Exactly three tags - Summary length
requirement - Proper JSON structure

Corrects issues if needed.

### Finalizer

Produces the final polished JSON output with strict formatting rules and improved tag specificity.
------------------------------------------------------------------------

## How to Run

1.  Install Ollama and pull the model:

ollama pull smollm:1.7b

2.  Run the Python script:

python agents_demo.py

The console will display: - Planner output - Reviewer output - Finalized JSON result
------------------------------------------------------------------------

## Conclusion

This project demonstrates integration of frontend development, containerized deployment, and local LLM-based agent workflows. It highlights practical implementation of modern JavaScript patterns alongside structured AI-driven content processing.
