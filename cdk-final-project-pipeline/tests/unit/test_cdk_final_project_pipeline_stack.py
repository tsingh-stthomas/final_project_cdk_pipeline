import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_final_project_pipeline.cdk_final_project_pipeline_stack import CdkFinalProjectPipelineStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_final_project_pipeline/cdk_final_project_pipeline_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkFinalProjectPipelineStack(app, "cdk-final-project-pipeline")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
