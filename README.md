# lentics-shipstation

This project contains source code and supporting files for a serverless application that automates ShipStation order processing, running on a daily schedule.

## Architecture Decision

This Lambda function is intentionally designed as a larger, monolithic application rather than multiple smaller functions. Here's why:

- **Execution Pattern**: The application runs once per day as a batch job, where cost efficiency is more important than startup speed
- **Simplicity**: Using a single function simplifies deployment, monitoring, and maintenance
- **Resource Efficiency**: For infrequent execution (minutes per day), a single Lambda provides better cost optimization than multiple functions or containers

While this approach differs from typical microservice Lambda patterns, it was chosen deliberately to match the specific requirements of this use case. The application leverages Lambda's pay-per-use model for an infrequent batch process while avoiding unnecessary infrastructure complexity.

The application uses several AWS resources, including Lambda functions, EventBridge for scheduling, and S3 for log storage. These resources are defined in the `template.yaml` file in this project.

## Deploy the sample application

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

To build and deploy your application for the first time, run the following in your shell:

```bash
sam build --use-container
sam deploy --guided
```
```