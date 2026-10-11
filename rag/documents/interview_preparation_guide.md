# Technical Interview Preparation Guide — AI/ML and Software Engineering

## Types of Interviews

### 1. Technical Screening (30–45 min)
- Basic coding questions (arrays, strings, loops)
- Questions about your resume and projects
- Conceptual ML/AI questions
- Usually conducted by a recruiter or junior engineer

### 2. Technical Deep Dive (60–90 min)
- Data structures and algorithms (LeetCode style)
- System design for experienced candidates (3+ years)
- ML fundamentals and model evaluation
- Live coding in an IDE or shared editor

### 3. ML-Specific Interview
- Explain your ML projects in detail
- Walk through model selection, feature engineering, evaluation
- Questions on overfitting, regularization, bias-variance tradeoff
- Hands-on ML problem solving

### 4. Behavioral Interview (STAR format)
- Tell me about a challenging project
- How did you handle a disagreement with a teammate?
- Describe a time you failed and what you learned

## Core ML Topics to Prepare

### Supervised Learning
- Linear/Logistic Regression: assumptions, regularization (L1/L2)
- Decision Trees, Random Forest, Gradient Boosting
- Support Vector Machines
- When to use which algorithm

### Model Evaluation
- Train/validation/test split rationale
- Cross-validation: k-fold, stratified k-fold
- Metrics: accuracy, precision, recall, F1, ROC-AUC
- Confusion matrix interpretation
- Handling class imbalance (SMOTE, class_weight)

### Feature Engineering
- Handling missing values
- Encoding categorical variables (one-hot, target encoding)
- Feature scaling (StandardScaler, MinMaxScaler)
- Feature selection techniques

### Overfitting and Regularization
- Bias-variance tradeoff
- L1 (Lasso), L2 (Ridge), ElasticNet regularization
- Dropout in neural networks
- Early stopping
- Cross-validation for model selection

### Deep Learning Basics
- Activation functions (ReLU, sigmoid, softmax)
- Backpropagation
- Batch normalization
- CNN, RNN, LSTM architecture basics
- Transfer learning concept

### NLP and Transformers
- TF-IDF and word embeddings (Word2Vec, GloVe)
- BERT architecture basics
- Fine-tuning pre-trained models
- RAG architecture: retrieval + generation

## Common Python/ML Coding Questions

1. Implement k-means clustering from scratch
2. Write a function to compute ROC-AUC without sklearn
3. Implement gradient descent for linear regression
4. Explain and code a decision tree split criterion
5. Write a custom preprocessing pipeline with sklearn

## System Design for ML (Senior Roles)

Topics covered:
- Feature store design
- Model serving at scale (REST API vs gRPC)
- A/B testing ML models
- Model monitoring and drift detection
- Data pipeline design (batch vs streaming)

## Questions to Ask the Interviewer

1. What does the ML infrastructure look like currently?
2. How do you handle model monitoring and retraining?
3. What is the biggest technical challenge the team is facing?
4. How do you balance research vs engineering in this role?
5. What does success look like in the first 90 days?

## Resources for Interview Prep

- LeetCode (leetcode.com) — coding problems
- ML Study Guide by Google
- Grokking the Machine Learning Interview (Educative)
- StatQuest with Josh Starmer (YouTube) — ML concepts
- Kaggle (kaggle.com) — hands-on ML practice
- CS229 Stanford ML Course — theory foundation
