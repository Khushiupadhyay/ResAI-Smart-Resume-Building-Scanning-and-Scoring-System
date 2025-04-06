// Import Firebase modules
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-app.js";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, GoogleAuthProvider, signInWithPopup } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-auth.js";
import { getFirestore, setDoc, doc } from "https://www.gstatic.com/firebasejs/10.11.1/firebase-firestore.js";

// Firebase Configuration
const firebaseConfig = {
    apiKey: "AIzaSyA9LzRejccPG1pCz6JP9gOTjAL6Y0vbpkk",
    authDomain: "codifiers-2025.firebaseapp.com",
    projectId: "codifiers-2025",
    storageBucket: "codifiers-2025.firebasestorage.app",
    messagingSenderId: "962513669675",
    appId: "1:962513669675:web:ed60884c3b3adac509e46e",
    measurementId: "G-1QYX1H8K1R"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth();
const db = getFirestore();
const provider = new GoogleAuthProvider();

// Function to display messages
function showMessage(message, divId) {
    var messageDiv = document.getElementById(divId);
    messageDiv.style.display = "block";
    messageDiv.innerHTML = message;
    messageDiv.style.opacity = 1;
    setTimeout(() => {
        messageDiv.style.opacity = 0;
    }, 5000);
}

// Signup with Email & Password
document.getElementById('submitSignUp').addEventListener('click', (event) => {
    event.preventDefault();
    const email = document.getElementById('rEmail').value;
    const password = document.getElementById('rPassword').value;
    const firstName = document.getElementById('fName').value;
    const lastName = document.getElementById('lName').value;

    createUserWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            const user = userCredential.user;
            const userData = {
                email: email,
                firstName: firstName,
                lastName: lastName
            };
            showMessage('Account Created Successfully', 'signUpMessage');

            setDoc(doc(db, "users", user.uid), userData)
                .then(() => {
                    window.location.href = 'homepage.html';
                })
                .catch((error) => {
                    console.error("Error writing document", error);
                });
        })
        .catch((error) => {
            const errorCode = error.code;
            if (errorCode == 'auth/email-already-in-use') {
                showMessage('Email Address Already Exists !!!', 'signUpMessage');
            } else {
                showMessage('Unable to create User', 'signUpMessage');
            }
        });
});

// Sign-In with Email & Password
document.getElementById('submitSignIn').addEventListener('click', (event) => {
    event.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    signInWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            showMessage('Login is successful', 'signInMessage');
            const user = userCredential.user;
            localStorage.setItem('loggedInUserId', user.uid);
            window.location.href = 'homepage.html';
        })
        .catch((error) => {
            const errorCode = error.code;
            if (errorCode === 'auth/invalid-credential') {
                showMessage('Incorrect Email or Password', 'signInMessage');
            } else {
                showMessage('Account does not Exist', 'signInMessage');
            }
        });
});

// Google Sign-In
document.getElementById('googleSignIn').addEventListener('click', () => {
    signInWithPopup(auth, provider)
        .then((result) => {
            const user = result.user;
            const userData = {
                email: user.email,
                firstName: user.displayName.split(' ')[0],
                lastName: user.displayName.split(' ')[1] || ''
            };
            localStorage.setItem('loggedInUserId', user.uid);
            
            setDoc(doc(db, "users", user.uid), userData, { merge: true })
                .then(() => {
                    window.location.href = 'homepage.html';
                })
                .catch((error) => {
                    console.error("Error writing document", error);
                });
        })
        .catch((error) => {
            console.error("Error during Google Sign-In", error);
            showMessage('Google Sign-In failed', 'signInMessage');
        });
});
