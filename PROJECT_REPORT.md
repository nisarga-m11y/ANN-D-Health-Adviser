# PROJECT REPORT
## Personalized Health Advice and Symptom Checking Chatbot

**Submitted by:** [Your Name]  
**USN/Roll No.:** [Your Roll Number]  
**Department:** Bachelor of Computer Applications  
**College:** [Your College Name]  
**Academic Year:** 2025-2026  
**Internal Guide:** [Guide Name]  
**External Guide:** [Guide Name]

---

## CERTIFICATE

This is to certify that the project entitled **"Personalized Health Advice and Symptom Checking Chatbot"** is a bonafide work carried out by **[Your Name]** in partial fulfillment of the requirements for the award of the degree of Bachelor of Computer Applications. This project has been completed under the guidance of **[Guide Name]** and has not been submitted earlier for the award of any degree or diploma.

**Place:** [Place]  
**Date:** [Date]

**Signature of Guide**  
**Signature of Head of the Department**  
**Signature of Principal**  
**Signature of Student**

---

## DECLARATION

I, **[Your Name]**, hereby declare that the project report titled **"Personalized Health Advice and Symptom Checking Chatbot"** is an original work carried out by me under the guidance of **[Guide Name]**. I further declare that this report has not been submitted to any other university, institution, or organization for the award of any degree or diploma.

**Place:** [Place]  
**Date:** [Date]  
**Signature of Student**

---

## ACKNOWLEDGEMENT

I express my sincere gratitude to **[Principal Name]**, Principal of **[College Name]**, for providing me with the opportunity to undertake this project.

I am deeply thankful to **[HOD Name]**, Head of the Department of BCA, for the valuable support, encouragement, and guidance provided throughout the project work.

I sincerely thank **[Guide Name]**, my internal guide, for the continuous guidance, useful suggestions, and motivation given during the preparation of this project. The feedback and direction provided by my guide helped me improve the quality of the work at every stage.

I also thank my parents, friends, and classmates for their support and encouragement during the development of this project. Their help and confidence motivated me to complete the work successfully.

Finally, I express my gratitude to all those who directly or indirectly helped me in completing this project.

---

## ABSTRACT

The project **"Personalized Health Advice and Symptom Checking Chatbot"** is a full-stack web application developed to help users describe symptoms in natural language and receive AI-assisted health guidance. The system combines a Django backend, a React frontend, machine learning, natural language processing, and database storage to create an interactive symptom-checking platform.

The chatbot accepts text input, voice input, and image-based input. Users can type symptoms such as fever, cough, headache, stomach pain, weakness, or similar problems, and the application predicts a likely disease pattern using a trained machine learning model. The system also generates health advice, safety warnings, and medicine-related suggestions where appropriate. In addition to symptom prediction, the application supports OTP-based authentication, chat history tracking, health report generation, prescription image assistance, medicine image identification, and emergency call configuration.

The backend is implemented using Django and Django REST Framework, while the frontend is built using React.js and Vite. The machine learning component uses TF-IDF vectorization and Naive Bayes classification trained on symptom-disease data. The application also supports multilingual interaction, including English and Kannada, along with text-to-speech and speech-to-text features for accessibility.

This system is intended for educational and supportive health guidance only. It is not a replacement for a licensed medical professional. The main objective of the project is to provide a user-friendly health assistant that can help users understand symptoms quickly, maintain chat records, and access basic self-care suggestions in a simple and structured manner.

---

## TABLE OF CONTENTS

1. Introduction  
   1.1 Introduction  
   1.2 Problem Statement  
   1.3 Need of the System  
   1.4 Scope of the Project  
   1.5 Objectives  
   1.6 Project Summary

2. System Analysis  
   2.1 Existing System  
   2.2 Limitations of Existing System  
   2.3 Proposed System  
   2.4 Feasibility Study  
   2.5 Project Planning  
   2.6 Advantages of Proposed System

3. Development Environment  
   3.1 Reason for Choosing Django  
   3.2 Reason for Choosing React and Vite  
   3.3 Reason for Choosing MySQL and SQLite  
   3.4 Reason for Choosing Scikit-Learn and NLTK  
   3.5 Authentication and API Layer  
   3.6 Additional Services Used

4. System Design  
   4.1 Architecture Design  
   4.2 High Level Design  
   4.3 Detailed Design  
   4.4 Modularization Details  
   4.5 Data Flow Description  
   4.6 Use Case Description  
   4.7 Database Design  
   4.8 Constraints and Validation

5. Hardware and Software Requirements  
   5.1 Hardware Requirements  
   5.2 Software Requirements  
   5.3 External Interface Requirements

6. Implementation  
   6.1 Frontend Implementation  
   6.2 Backend Implementation  
   6.3 Machine Learning Implementation  
   6.4 Natural Language Processing Implementation  
   6.5 Chat History and Health Report Implementation  
   6.6 Voice and Multilingual Features  
   6.7 Image Handling Features  
   6.8 Emergency and Safety Features  
   6.9 Key API Endpoints Used

7. Testing  
   7.1 Purpose of Testing  
   7.2 Types of Testing Performed  
   7.3 Test Cases  
   7.4 Walkthroughs and Demo  
   7.5 Observations from Testing

8. Screenshots  

9. Conclusion  

10. Future Enhancement  

11. References

---

# 1. INTRODUCTION

## 1.1 Introduction

Health-related problems are among the most common concerns faced by people in daily life. Many users are often unsure about the meaning of early symptoms such as fever, cough, headache, cold, stomach pain, dizziness, or fatigue. In such cases, people usually search the internet, ask relatives, or wait until the symptoms become severe. This often leads to confusion because online information is not always reliable, and symptom interpretation can be difficult for a non-medical person.

The proposed system is a **Personalized Health Advice and Symptom Checking Chatbot** that provides an interactive way to understand symptom patterns. The system allows a user to type health-related complaints in simple language. The chatbot then processes the input, predicts a possible disease pattern, and returns a response with advice, caution notes, and helpful next-step suggestions. The project uses machine learning and natural language processing to improve the quality of analysis and to make the response more intelligent than a fixed rule-based chatbot.

The system is developed as a web application so that users can access it easily from a browser. The frontend is designed in React.js, which gives a smooth and responsive user interface. The backend is created using Django and Django REST Framework, which handle authentication, prediction requests, chat history, and health report generation. The database stores user details, conversation history, ratings, and analysis records so that users can review earlier interactions later.

The project also includes voice input, text-to-speech, image-based medicine guidance, prescription assistance, and emergency call support. These additional features make the application more practical and user friendly. The final result is a modern, supportive health assistant that can guide the user in a simple and accessible way.

## 1.2 Problem Statement

People often experience symptoms before they understand the seriousness of the condition. In many cases, they do not know whether the problem is minor or requires urgent medical attention. There is a need for a system that can accept natural language health queries, analyze symptom patterns, provide possible disease predictions, and give advice in a fast and simple way.

Manual consultation for every small symptom is not always practical, and generic internet searches often produce misleading results. Therefore, an intelligent health chatbot is useful for basic symptom checking, self-care suggestions, and better organization of health-related information.

## 1.3 Need of the System

The need for this system arises from the following points. First, many users require quick guidance when they feel unwell. Second, a conversational interface is easier than filling complicated medical forms. Third, users benefit from having their chat history stored so that they can review symptoms later. Fourth, multilingual support makes the application more accessible to a wider audience. Fifth, a system that combines text, voice, and image input can support users with different comfort levels and communication styles.

## 1.4 Scope of the Project

The scope of this project includes symptom-based disease prediction, health advice generation, user authentication, chat history maintenance, language translation, voice handling, medicine image identification, prescription assistance, emergency call configuration, and health report generation. The system is not intended to replace a doctor. Its scope is limited to educational and supportive guidance for basic symptom understanding.

## 1.5 Objectives

The main objectives of the project are to develop a user-friendly chatbot for symptom checking, to store and manage user conversations securely, to use machine learning for disease pattern prediction, to support text, voice, and image input, to provide basic medicine and self-care suggestions, and to generate a history-based health report for the user.

## 1.6 Project Summary

This project is a complete web-based health assistant that combines frontend design, backend APIs, database storage, and machine learning into one working application. The user can register, log in, describe symptoms, receive predictions, and view previous reports. The same application also supports medicine images, prescription guidance, and voice interaction. This makes the project both technically interesting and practically useful.

---

# 2. SYSTEM ANALYSIS

## 2.1 Existing System

In the existing process, users usually search their symptoms manually on the internet or consult people around them for advice. This process is slow, inconsistent, and often confusing. Medical websites often provide large amounts of information, but they do not personalize responses according to the user’s exact input. A person may type symptoms and receive many unrelated search results, which makes it difficult to decide what to do next.

Traditional systems also do not store the user’s previous health queries in a structured way. This means users cannot easily compare symptoms over time or check whether a condition is improving or worsening. In many cases, a user may also struggle to explain symptoms in English, and some users are more comfortable speaking than typing.

## 2.2 Limitations of the Existing System

The existing method has several limitations. It is not interactive, it does not remember past conversations, it cannot analyze symptom combinations in a structured way, and it does not provide a personalized conversation experience. It also lacks voice interaction, multilingual support, and medicine image assistance. Most importantly, the user must manually interpret the search results, which is not always reliable.

## 2.3 Proposed System

The proposed system solves these problems by providing an intelligent chatbot interface. The user can enter symptoms in simple language, upload relevant images, or use voice input. The system processes the text using NLP techniques, applies a trained machine learning model, and produces a likely disease pattern with advice. The backend stores the results in the database, and the frontend displays them in an easy-to-read chat format.

The proposed system is modular and extendable. It includes authentication, prediction, chat history, report generation, image analysis, medicine identification, prescription support, and emergency call integration. The application is designed to be responsive and can be used on both desktop and mobile devices.

## 2.4 Feasibility Study

The project is technically feasible because the selected technologies are widely supported and well documented. Django supports secure API development and database integration. React provides a fast and responsive frontend. Scikit-learn is suitable for text classification tasks. NLTK supports text preprocessing. MySQL and SQLite can reliably store user and chat data. The hardware requirements are modest, so the project can run on a standard laptop.

The project is economically feasible because it uses mostly open-source tools. Django, React, Vite, MySQL, Scikit-learn, and NLTK are free to use. The optional APIs and calling services can be enabled only when needed. This keeps the overall cost low.

The project is operationally feasible because the user interface is simple and interactive. The user only needs to type symptoms, upload an image, or speak into the microphone. The system does not require medical expertise to operate.

## 2.5 Project Planning

The project was planned in a step-by-step manner. The first stage was requirement collection and understanding the problem statement. The second stage was design of backend, frontend, and database structure. The third stage was implementation of authentication, chatbot, and prediction features. The fourth stage was integration of ML model, image support, and voice features. The fifth stage was testing, correction, and final polishing of the interface.

## 2.6 Advantages of the Proposed System

The proposed system is faster than manual searching, easier to use, and more organized. It supports multiple input methods, stores history, and generates advice in a structured form. It can also help users understand symptom patterns more clearly and encourage them to seek proper medical care when necessary.

---

# 3. DEVELOPMENT ENVIRONMENT

## 3.1 Reason for Choosing Django

Django was chosen for the backend because it is a secure and reliable web framework. It supports rapid development, database integration, authentication, admin tools, and REST API creation. The project needs a backend that can manage users, chat history, and ML response generation, and Django fits these requirements well. Django REST Framework makes it easy to create clean API endpoints for the React frontend.

## 3.2 Reason for Choosing React and Vite

React was chosen for the frontend because it is ideal for building responsive single-page applications. The chatbot interface needs dynamic updates, message rendering, file upload handling, and state management, all of which are well supported by React. Vite was selected as the build tool because it provides fast development startup, quick rebuilds, and a simple modern setup.

## 3.3 Reason for Choosing MySQL and SQLite

The project supports both SQLite and MySQL. SQLite is useful for easy local development because it requires little setup. MySQL is useful for a more permanent database environment and is better suited for structured storage of users, history, and analysis data. The settings file is designed so that the project can switch between SQLite and MySQL depending on the environment.

## 3.4 Reason for Choosing Scikit-Learn and NLTK

Scikit-learn is suitable for classification tasks such as symptom-to-disease prediction. It provides TF-IDF vectorization, train-test splitting, and Naive Bayes classification. NLTK is used for preprocessing the symptom text before training and prediction. This combination is simple, effective, and appropriate for a student-level machine learning project.

## 3.5 Authentication and API Layer

The backend uses token-based authentication. When a user registers or logs in, a token is generated and sent to the frontend. The frontend stores the token and sends it with future requests. This method makes the system secure and easy to manage. The API layer exposes endpoints for login, registration, symptom prediction, chat messages, image analysis, voice input, translation, chat history, severity updates, and text-to-speech.

## 3.6 Additional Services Used

The system also supports optional features such as email OTP, mobile OTP simulation, text-to-speech output, Kannada support, image processing, and emergency callback integration. These services improve usability and make the chatbot more practical for real-world use.

---

# 4. SYSTEM DESIGN

## 4.1 Architecture Design

The architecture of the system follows a frontend-backend-database model. The React frontend collects the user input. The request is then sent to Django REST APIs. The backend performs validation, preprocessing, prediction, and response generation. The result is stored in the database and returned to the frontend. The frontend displays the response in the chat interface and also updates the health report page.

The main flow is as follows: user input is entered in the browser, the frontend sends the data to the backend, the backend normalizes the text and applies NLP preprocessing, the trained machine learning model predicts the most likely disease pattern, and the backend returns advice, medicine suggestions, and safety guidance.

**Figure 1:** System Architecture Diagram  
Use the diagram from [docs/ai-health-chatbot-diagram.svg](/c:/Users/Hp/chatbot/docs/ai-health-chatbot-diagram.svg)

## 4.2 High Level Design

At a high level, the system contains four major parts. The first is the authentication module, which manages registration, login, OTP verification, and user profile details. The second is the chatbot module, which handles symptom input, prediction, voice, image, and advice generation. The third is the data storage module, which stores chat history, ratings, and image analysis records. The fourth is the report module, which summarizes previous user interactions.

## 4.3 Detailed Design

The detailed design covers the internal structure of each module. In the backend, the `accounts` app handles user registration and login. The `chatbot` app handles all chatbot-related functionality. The `services.py` file contains the analysis logic, including text normalization, symptom preprocessing, machine learning prediction, medicine guidance, image classification, and translation helpers. The `views.py` file exposes the APIs to the frontend. The serializers validate the input data before it reaches the service layer.

On the frontend, the `HomePage`, `RegisterPage`, `OtpAuthPage`, `ChatbotDashboard`, and `HealthReportPage` components provide the user interface. The dashboard is the central screen where the user interacts with the chatbot. It includes message display, quick prompts, microphone support, file upload controls, emergency actions, and notification elements.

## 4.4 Modularization Details

The application is divided into the following modules: authentication, symptom prediction, chat history, voice chat, image analysis, medicine recognition, prescription assistance, severity follow-up, emergency call support, and health report generation. This modular design makes the system easier to maintain and expand.

## 4.5 Data Flow Description

The user first logs in or registers. After authentication, the user enters symptoms in the dashboard. The frontend sends the message to the backend. The backend cleans the text, applies preprocessing, and passes it through the trained model. The predicted disease, advice, and suggestion text are then returned. If the user uploads an image, the backend checks whether it is a medicine photo, prescription, skin rash image, or eye redness image and processes it accordingly. The chat record is stored in the database, and the health report page later reads the history and summarizes it.

**Figure 2:** Data Flow Diagram  
Use the diagram from [docs/dfd-ann-d.svg](/c:/Users/Hp/chatbot/docs/dfd-ann-d.svg)

## 4.6 Use Case Description

The main actor in the system is the user. The user can register, log in, send a symptom message, upload an image, use voice input, request advice, view chat history, view the health report, and request emergency-related support. The system responds by validating the input, predicting the likely condition, and storing the interaction.

**Figure 3:** Use Case Diagram  
Use the diagram from [docs/usecase-ann-d.svg](/c:/Users/Hp/chatbot/docs/usecase-ann-d.svg)

## 4.7 Database Design

The database design includes several important tables. The `users` table stores user details such as name, email, phone number, and authentication fields. The `chat_history` table stores messages, responses, predicted diseases, advice, timestamps, and uploaded images. The `symptoms_data` table stores the training data used for the machine learning component. The `symptom_image_analysis` table stores image-based analysis records. The `chat_rating` table stores feedback and ratings for conversations. The `logout_feedback` table stores end-session feedback.

## 4.8 Constraints and Validation

The system validates user input before processing it. Messages have a maximum length limit. Image uploads are restricted to valid file types and size limits. Audio files are also size checked. Phone numbers for callback requests must follow E.164 format. These constraints help avoid invalid requests and improve system reliability.

---

# 5. HARDWARE AND SOFTWARE REQUIREMENTS

## 5.1 Hardware Requirements

The project can run on a standard computer or laptop. A minimum configuration includes a dual-core processor, 4 GB RAM, and sufficient storage for the project files and database. For smoother development, 8 GB RAM or more is recommended. A webcam or microphone is optional for voice-related features, but not mandatory.

## 5.2 Software Requirements

The software requirements include Windows 10 or higher, Python 3.x, Node.js 18 or higher, Django, Django REST Framework, React, Vite, MySQL or SQLite, Scikit-learn, NLTK, Axios, and a modern browser such as Chrome or Edge. The system also uses optional internet-based services for text-to-speech, translation, and some advanced analysis functions.

## 5.3 External Interface Requirements

The project requires a browser-based user interface. The frontend communicates with the backend through API calls. Optional external interfaces include email configuration for OTP, speech synthesis services, and callback services. These are controlled through environment variables so the application can work in different environments.

---

# 6. IMPLEMENTATION

## 6.1 Frontend Implementation

The frontend is implemented in React.js. The `App.jsx` file handles routing between home, login, register, dashboard, and health report pages. The dashboard is the central page where users interact with the chatbot. The UI is designed to be modern and conversational. It displays the chatbot messages, user messages, upload controls, quick prompts, and emergency action buttons.

The frontend communicates with the backend through Axios API functions defined in the `api` folder. These functions send chat messages, voice files, image files, and authentication requests. The frontend also stores the authentication token and uses it automatically for protected routes. The health report page fetches chat history and displays the summary of previous results.

## 6.2 Backend Implementation

The backend is implemented using Django and Django REST Framework. The settings file defines the installed apps, token authentication, CORS settings, media storage, environment variables, and database configuration. The `accounts` app manages user registration, login, OTP verification, and logout feedback. The `chatbot` app manages predictions, history, image analysis, voice handling, severity updates, and text-to-speech generation.

The backend uses custom serializers to validate incoming requests. The views layer connects the HTTP requests to the service logic. The service layer performs the core medical text processing and prediction tasks. This separation of responsibilities makes the code easier to maintain and test.

## 6.3 Machine Learning Implementation

The ML pipeline begins with a CSV file containing symptom descriptions and disease labels. The `train_model.py` script loads the data, preprocesses the text, converts it into TF-IDF features, encodes the disease labels, and trains a Multinomial Naive Bayes classifier. After training, the model, vectorizer, and label encoder are saved as pickle files.

During runtime, the backend loads the trained model and applies it to the user’s symptom text. It also supports fallback patterns for common symptom combinations. This improves robustness and helps produce a useful response even when the input is short or informal.

## 6.4 Natural Language Processing Implementation

NLP is used to prepare the user input for prediction. The text is normalized, stop words are removed, and symptom phrases are cleaned before classification. The system also supports Kannada hints and translation logic so that the user can interact in a more natural way. This helps the chatbot understand practical language rather than only strict medical terms.

## 6.5 Chat History and Health Report Implementation

Every successful interaction is stored in the `chat_history` table. The backend returns the latest chat records through the history API. The health report page reads this data and creates a summary of repeated disease predictions and recent advice entries. This gives the user a simple record of their previous symptom checks.

## 6.6 Voice and Multilingual Features

The chatbot supports voice input through browser speech recognition and voice output through text-to-speech. The backend can generate audio responses in English or Kannada. This makes the system more accessible for users who are not comfortable typing. The voice feature is especially useful for quick symptom descriptions.

## 6.7 Image Handling Features

The project includes image-based features for symptom analysis, prescription review, and medicine identification. The system can classify whether an uploaded image is a medicine photo, prescription, skin issue, or eye issue. It then generates a cautious, structured response. Medicine images are matched against a local image catalog when possible, and prescriptions can be reviewed with basic guidance. This adds a practical visual support layer to the chatbot.

## 6.8 Emergency and Safety Features

The system includes emergency call configuration and callback request support. It also shows a safety warning whenever the symptoms seem serious. The chatbot is deliberately cautious and reminds the user to seek medical attention when needed. This safety-first design is important because the application is meant for guidance, not diagnosis.

## 6.9 Key API Endpoints Used

The application includes endpoints for registration, login, user profile retrieval, chat prediction, chat message handling, history retrieval, severity updates, image analysis, prescription support, medicine support, voice upload, translation, text-to-speech, call configuration, callback request, and rating submission. These APIs allow the frontend to perform all major functions through a clean and organized interface.

---

# 7. TESTING

## 7.1 Purpose of Testing

Testing is done to ensure that the system works correctly, responds properly to valid and invalid inputs, and maintains the expected behavior across all modules. Since the project includes authentication, file upload, machine learning, and database operations, testing is necessary to make sure the application remains stable and user friendly.

## 7.2 Types of Testing Performed

The system was tested through manual testing and integration testing. Manual testing was used to check the user interface, login flow, message sending, and report generation. Integration testing was used to verify that the frontend and backend communicate correctly through API calls. Functional testing was done to check whether each feature performs its intended task.

## 7.3 Test Cases

| Test Case | Input | Expected Result | Result |
|---|---|---|---|
| User registration | Valid name, email, password | Account created and token returned | Passed |
| User login | Correct email and password | User authenticated successfully | Passed |
| Empty symptom input | Blank message | Validation error or disabled send | Passed |
| Symptom prediction | Fever, cough, body pain | Likely disease and advice returned | Passed |
| Chat history load | Open health report page | Previous conversations displayed | Passed |
| Voice input | Spoken symptom sentence | Text captured and sent | Passed |
| Invalid image upload | Non-image file | Error message returned | Passed |
| Medicine image upload | Clear medicine image | Medicine information shown | Passed |
| Prescription image upload | Prescription photo | Prescription assistance response returned | Passed |
| Severity selection | Mild / moderate / severe | Updated advice response returned | Passed |

## 7.4 Walkthroughs and Demo

The system was reviewed by checking the complete user flow from registration to report generation. The chatbot was tested with common symptom phrases and image inputs. The report page was tested by loading stored chat history. The callback and emergency UI were also tested to ensure they behave correctly under configured conditions.

## 7.5 Observations from Testing

The testing showed that the chatbot can handle text-based health queries, store conversations properly, and display health summaries. The voice and image features improved usability. The validation rules prevented most invalid submissions. The system behaved consistently in local development and handled the main workflow smoothly.

---

# 8. SCREENSHOTS

In the final project file, add the following screenshots with captions.

1. Home page screenshot showing the project landing page.  
2. Registration page screenshot showing new user sign-up.  
3. Login or OTP page screenshot showing authentication.  
4. Chatbot dashboard screenshot showing the conversation interface.  
5. Symptom prediction result screenshot showing disease prediction and advice.  
6. Voice input screenshot showing microphone interaction.  
7. Medicine image analysis screenshot showing medicine details.  
8. Prescription upload screenshot showing prescription assistance.  
9. Health report page screenshot showing prediction summary and recent advice.  
10. Emergency call modal or callback screen screenshot.

Each screenshot should have a short caption describing the purpose of the screen.

---

# 9. CONCLUSION

The project **"Personalized Health Advice and Symptom Checking Chatbot"** successfully demonstrates how machine learning, natural language processing, and modern web development can be combined to build a useful health support system. The application provides a simple way for users to describe symptoms, receive likely disease pattern predictions, and get supportive advice in an organized format.

The project also includes chat history, health reporting, voice support, image-based assistance, multilingual handling, and emergency-oriented features. These additions make the system more practical and user friendly. The use of Django on the backend and React on the frontend gives the application a clean and scalable structure. The database design supports persistent storage of users and health conversations, while the machine learning component adds intelligence to the symptom analysis process.

Overall, this project helped in understanding full-stack application development, API integration, model training, database handling, and user interface design. It also showed how technology can be used to create a supportive health assistant that helps users make better decisions about their symptoms. At the same time, the system remains cautious and repeatedly emphasizes that it is not a replacement for professional medical diagnosis.

---

# 10. FUTURE ENHANCEMENT

The project can be improved further in several ways. A more advanced deep learning model can be added to improve disease prediction accuracy. The dataset can be expanded to include more symptoms and more disease classes. A doctor appointment booking feature can be added so that the chatbot can connect the user to a real consultation when needed. A lab report upload feature can also be added for smarter health summaries.

In future, the application can support more Indian languages and can include speech-to-speech interaction. A better emergency contact system can be added with location-based service recommendations. A medication reminder module, allergy tracking module, and family health timeline module can also be useful. The image module can be expanded to support clearer medicine recognition and more detailed prescription understanding. A mobile app version can also be developed for easier daily usage.

---

# 11. REFERENCES

1. [README.md](/c:/Users/Hp/chatbot/README.md)  
2. [backend/config/settings.py](/c:/Users/Hp/chatbot/backend/config/settings.py)  
3. [backend/apps/accounts/models.py](/c:/Users/Hp/chatbot/backend/apps/accounts/models.py)  
4. [backend/apps/accounts/serializers.py](/c:/Users/Hp/chatbot/backend/apps/accounts/serializers.py)  
5. [backend/apps/accounts/views.py](/c:/Users/Hp/chatbot/backend/apps/accounts/views.py)  
6. [backend/apps/chatbot/models.py](/c:/Users/Hp/chatbot/backend/apps/chatbot/models.py)  
7. [backend/apps/chatbot/serializers.py](/c:/Users/Hp/chatbot/backend/apps/chatbot/serializers.py)  
8. [backend/apps/chatbot/views.py](/c:/Users/Hp/chatbot/backend/apps/chatbot/views.py)  
9. [backend/apps/chatbot/services.py](/c:/Users/Hp/chatbot/backend/apps/chatbot/services.py)  
10. [backend/ml/train_model.py](/c:/Users/Hp/chatbot/backend/ml/train_model.py)  
11. [frontend/src/App.jsx](/c:/Users/Hp/chatbot/frontend/src/App.jsx)  
12. [frontend/src/pages/ChatbotDashboard.jsx](/c:/Users/Hp/chatbot/frontend/src/pages/ChatbotDashboard.jsx)  
13. [frontend/src/pages/HealthReportPage.jsx](/c:/Users/Hp/chatbot/frontend/src/pages/HealthReportPage.jsx)  
14. Django REST Framework documentation  
15. React documentation  
16. Scikit-learn documentation  
17. NLTK documentation

---

## APPENDIX A: PROJECT FLOW SUMMARY

1. User opens the application in a browser.  
2. User registers or logs in.  
3. User enters symptoms using text, voice, or image.  
4. Backend validates and preprocesses the input.  
5. The machine learning model predicts the likely condition.  
6. The chatbot generates advice and safety guidance.  
7. The conversation is stored in the database.  
8. User can later open the health report page and review past results.  

## APPENDIX B: KEY FEATURES IMPLEMENTED

1. User registration and login  
2. OTP-based authentication flow  
3. Symptom-based disease prediction  
4. Chat history storage  
5. Health report summary page  
6. Voice input support  
7. Text-to-speech support  
8. Kannada language support  
9. Prescription image assistance  
10. Medicine image identification  
11. Emergency call configuration  
12. Severity-based response handling  

