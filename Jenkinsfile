pipeline {
    agent { docker { image 'python:3.8' } }

    environment {
        REPO_URL = "https://github.com/pranavp0/vuln-scanner.git"
    }

    stages {
        stage('Clone Repository') {
            steps {
                sh 'git clone $REPO_URL'
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
