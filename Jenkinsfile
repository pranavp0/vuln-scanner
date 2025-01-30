pipeline {
    agent {
        dockerContainer {
            image 'python:3.8'
            runArgs '--workdir /workspace'
        }
    }
    
    environment {
        REPO_URL = "https://github.com/pranavp0/vuln-scanner.git"
    }

    stages {
        stage('Setup Docker') {
            steps {
                script {
                    sh 'docker run --rm python:3.8 python --version'
                }
            }
        }
        
        stage('Clone Repository') {
            steps {
                sh 'git clone https://github.com/pranavp0/vuln-scanner.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t tidos-framework .'
            }
        }

        stage('Run TIDoS Security Tests') {
            steps {
                sh 'docker run --rm tidos-framework'
            }
        }
    }
}
