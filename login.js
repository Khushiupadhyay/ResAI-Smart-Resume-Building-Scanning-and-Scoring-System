// Initialize Firebase
import { initializeApp } from 'https://www.gstatic.com/firebasejs/9.6.0/firebase-app.js';
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, signInWithPopup, GoogleAuthProvider, onAuthStateChanged } from 'https://www.gstatic.com/firebasejs/9.6.0/firebase-auth.js';

const firebaseConfig = {
    apiKey: "AIzaSyA9LzRejccPG1pCz6JP9gOTjAL6Y0vbpkk",
    authDomain: "codifiers-2025.firebaseapp.com",
    projectId: "codifiers-2025",
    storageBucket: "codifiers-2025.firebasestorage.app",
    messagingSenderId: "962513669675",
    appId: "1:962513669675:web:ed60884c3b3adac509e46e",
    measurementId: "G-1QYX1H8K1R"
  };

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Get references to the DOM elements
const signUpForm = document.querySelector('.sign-up form');
const signInForm = document.querySelector('.sign-in form');
const googleSignUpButton = document.getElementById('google-signup');
const googleLoginButton = document.getElementById('google-login');

// Sign up with email and password
signUpForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const username = signUpForm.querySelector('input[type="text"]').value;
    const email = signUpForm.querySelector('input[type="email"]').value;
    const password = signUpForm.querySelector('input[type="password"]').value;
    const confirmPassword = signUpForm.querySelector('input[type="password"]').nextElementSibling.value;

    if (password !== confirmPassword) {
        alert("Passwords do not match");
        return;
    }

    createUserWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            // Signed in
            const user = userCredential.user;
            alert("User signed up successfully!");
            window.location.href = 'templates/index.html';
        })
        .catch((error) => {
            const errorCode = error.code;
            const errorMessage = error.message;
            alert(errorMessage);
        });
});

// Sign in with email and password
signInForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = signInForm.querySelector('input[type="text"]').value;
    const password = signInForm.querySelector('input[type="password"]').value;

    signInWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            // Signed in
            const user = userCredential.user;
            alert("User logged in successfully!");
            window.location.href = 'templates/index.html';
        })
        .catch((error) => {
            const errorCode = error.code;
            const errorMessage = error.message;
            alert(errorMessage);
        });
});

// Sign in with Google
const provider = new GoogleAuthProvider();

googleSignUpButton.addEventListener('click', () => {
    signInWithPopup(auth, provider)
        .then((result) => {
            // This gives you a Google Access Token. You can use it to access the Google API.
            const credential = GoogleAuthProvider.credentialFromResult(result);
            const token = credential.accessToken;
            // The signed-in user info.
            const user = result.user;
            alert("User signed up with Google successfully!");
            window.location.href = 'templates/index.html';
        }).catch((error) => {
            // Handle Errors here.
            const errorCode = error.code;
            const errorMessage = error.message;
            // The email of the user's account used.
            const email = error.email;
            // The AuthCredential type that was used.
            const credential = GoogleAuthProvider.credentialFromError(error);
            alert(errorMessage);
        });
});

googleLoginButton.addEventListener('click', () => {
    signInWithPopup(auth, provider)
        .then((result) => {
            // This gives you a Google Access Token. You can use it to access the Google API.
            const credential = GoogleAuthProvider.credentialFromResult(result);
            const token = credential.accessToken;
            // The signed-in user info.
            const user = result.user;
            alert("User logged in with Google successfully!");
            window.location.href = 'templates/index.html';
        }).catch((error) => {
            // Handle Errors here.
            const errorCode = error.code;
            const errorMessage = error.message;
            // The email of the user's account used.
            const email = error.email;
            // The AuthCredential type that was used.
            const credential = GoogleAuthProvider.credentialFromError(error);
            alert(errorMessage);
        });
});

// Optional: Listen for auth state changes
onAuthStateChanged(auth, (user) => {
    if (user) {
        // User is signed in, see docs for a list of available properties
        // https://firebase.google.com/docs/reference/js/firebase.User
        const uid = user.uid;
        alert("User is signed in with UID: " + uid);
    } else {
        // User is signed out
        alert("No user is signed in.");
    }
});