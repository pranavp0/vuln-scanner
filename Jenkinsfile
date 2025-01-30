pipeline {
    agent {
        docker {
            image 'python:3.8'
            args '--user root'  // Avoid permission issues inside container
        }
    }
    
    environment {
        REPO_URL = "https://github.com/pranavp0/vuln-scanner.git"
        WORKDIR = "/workspace"
    }

    stages {
        stage('Clone Repository') {
            steps {
                script {
                    sh 'rm -rf vuln-scanner || true'  // Remove existing repo (if any)
                    sh "git clone $REPO_URL"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    sh 'docker build -t tidos-framework vuln-scanner/'
                }
            }
        }

        stage('Run TIDoS Security Tests') {
            steps {
                script {
                    sh 'docker run --rm tidos-framework'
                }
            }
        }
    }
}
