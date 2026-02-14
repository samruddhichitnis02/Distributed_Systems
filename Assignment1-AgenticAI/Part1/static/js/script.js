// Part II - JavaScript Solutions

// Question 5: Closure to track form submission count
const createSubmissionCounter = () => {
    let count = 0;
    return () => {
        count++;
        console.log(`Form Submission Count: ${count}`);
        return count;
    };
};

const trackSubmission = createSubmissionCounter();

// Question 1: Arrow function to validate form
const validateForm = (e) => {
    e.preventDefault();

    const blogContent = document.getElementById('blogContent').value;
    const termsCheckbox = document.getElementById('terms');

    // Question 1a: Verify if blog content is more than 25 characters
    if (blogContent.length <= 25) {
        alert('Blog content should be more than 25 characters');
        return false;
    }

    // Question 1b: Verify if terms and conditions checkbox is checked
    if (!termsCheckbox.checked) {
        alert('You must agree to the terms and conditions');
        return false;
    }

    // If validation passes, process the form
    processFormSubmission(e);
    return true;
};

// Question 2, 3, 4: Process form submission
const processFormSubmission = (e) => {
    // Get form data
    const formData = {
        blogTitle: document.getElementById('blogTitle').value,
        authorName: document.getElementById('authorName').value,
        email: document.getElementById('email').value,
        blogContent: document.getElementById('blogContent').value,
        category: document.getElementById('category').value,
        termsAgreed: document.getElementById('terms').checked
    };

    // Question 2: Convert form data to JSON string and log to console
    const jsonString = JSON.stringify(formData, null, 2);
    console.log('='.repeat(60));
    console.log('FORM DATA AS JSON STRING:');
    console.log('='.repeat(60));
    console.log(jsonString);
    console.log('='.repeat(60));

    // Parse the JSON string back to object for next steps
    const parsedObject = JSON.parse(jsonString);

    // Question 3: Use object destructuring to extract title and email
    const { blogTitle: title, email } = parsedObject;
    console.log('\nDESTRUCTURED VALUES:');
    console.log('-'.repeat(60));
    console.log(`Title: ${title}`);
    console.log(`Email: ${email}`);
    console.log('-'.repeat(60));

    // Question 4: Use spread operator to add submissionDate
    const currentDateTime = new Date().toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    });

    const updatedObject = {
        ...parsedObject,
        submissionDate: currentDateTime
    };

    console.log('\nUPDATED OBJECT WITH SUBMISSION DATE:');
    console.log('-'.repeat(60));
    console.log(JSON.stringify(updatedObject, null, 2));
    console.log('-'.repeat(60));

    // Question 5: Track submission count using closure
    console.log('\n');
    trackSubmission();

    // Success message
    console.log('\n✅ Form submitted successfully!\n');

    // Show success alert to user
    alert('🎉 Blog published successfully! Check the console for details.');

    // Optional: Reset form after successful submission
    document.getElementById('blogForm').reset();
};

// Attach event listener when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('blogForm');
    form.addEventListener('submit', validateForm);

    console.log('🚀 Blog Form Application Loaded!');
    console.log('Fill out the form and submit to see the magic happen in the console.\n');
});