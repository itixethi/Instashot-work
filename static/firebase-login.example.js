'use strict';

// Import Firebase 
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-app.js";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-auth.js";

// Firebase config
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};

window.addEventListener("load", function () {
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    updateUI(document.cookie);
    console.log("Firebase initialized");
  
    // Sign Up
    const signUpBtn = document.getElementById("sign-up");
    if (signUpBtn) {
      signUpBtn.addEventListener("click", function () {
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;
  
        createUserWithEmailAndPassword(auth, email, password)
          .then((userCredential) => userCredential.user.getIdToken())
          .then((token) => {
            setCookie(token);
            window.location = "/";
          })
          .catch((error) => {
            console.error(error.code + " " + error.message);
          });
      });
    }
  
    // Login
    const loginBtn = document.getElementById("login");
    if (loginBtn) {
      loginBtn.addEventListener("click", function () {
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;
  
        signInWithEmailAndPassword(auth, email, password)
          .then((userCredential) => userCredential.user.getIdToken())
          .then((token) => {
            setCookie(token);
            window.location = "/";
          })
          .catch((error) => {
            console.error(error.code + " " + error.message);
          });
      });
    }
  
    // Sign Out
    const signOutBtn = document.getElementById("sign-out");
    if (signOutBtn) {
      signOutBtn.addEventListener("click", function () {
        signOut(auth)
          .then(() => {
            clearCookie();
            setTimeout(() => {
              updateUI("");
              window.location.href = "/logout";
            }, 300);
          })
          .catch((error) => {
            console.error("Logout error:", error);
          });
      });
    }
  });
  
  // Set Token Cookie
  function setCookie(token) {
    document.cookie = `token=${token};path=/;SameSite=Strict`;
  }
  
  // Clear Token Cookie
  function clearCookie() {
    document.cookie = "token=;path=/;SameSite=Strict;expires=Thu, 01 Jan 1970 00:00:00 GMT";
  }
  
  // UI Update Based on Token Presence
  function updateUI(cookie) {
    const token = parseCookieToken(cookie);
    const loginBox = document.getElementById("login-box");
    const signOutBtn = document.getElementById("sign-out");
  
    if (token.length > 0) {
      if (loginBox) loginBox.hidden = true;
      if (signOutBtn) signOutBtn.hidden = false;
    } else {
      if (loginBox) loginBox.hidden = false;
      if (signOutBtn) signOutBtn.hidden = true;
    }
  }
  
  // Extract Token from Cookie
  function parseCookieToken(cookie) {
    const parts = cookie.split(";");
    for (let i = 0; i < parts.length; i++) {
      const pair = parts[i].trim().split("=");
      if (pair[0] === "token") {
        return pair[1];
      }
    }
    return "";
  }