from aws_cdk import (
    aws_s3 as s3,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_iam as iam,
    aws_logs as logs,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_codepipeline_actions as codepipeline_actions,
    Stack,
    Aws,
    pipelines,
    RemovalPolicy
)

from constructs import Construct

class CdkFinalProjectPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        
        # Artifact Bucket
        artifact_bucket = s3.Bucket(
            self, "ArtifactBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Create a CodeCommit repository
        app_project_repo = codecommit.Repository(
            self, "JavaProjectRepo",
            repository_name="java-project",
            description="Repo for the Java project",
            code=codecommit.Code.from_directory("code_from_s3/java-project")
        )
        
        # Create the IAM role for CodeBuild
        code_build_role = iam.Role(
            self, "AppBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            path="/"
        )

        # Define policy statements
        s3_policy_statement = iam.PolicyStatement(
            sid="S3Permissions",
            actions=[
                "s3:PutObject",
                "s3:GetObject",
                "s3:GetObjectVersion",
                "s3:GetBucketAcl",
                "s3:GetBucketLocation"
            ],
            resources=[
                "arn:aws:s3:::artifact_bucket",
                "arn:aws:s3:::artifact_bucket/*"
            ],
            effect=iam.Effect.ALLOW
        )

        codecommit_policy_statement = iam.PolicyStatement(
            sid="CodeCommitPolicy",
            actions=["codecommit:GitPull"],
            resources=["*"],
            effect=iam.Effect.ALLOW
        )

        # Create and attach the policy to the role
        policy = iam.Policy(
            self, "CodeBuildAccess",
            policy_name="CodeBuildAccess",
            statements=[s3_policy_statement, codecommit_policy_statement]
        )
        code_build_role.attach_inline_policy(policy)
        
        # Create a CodeBuild project
        app_build_project = codebuild.Project(
            self, "AppBuildProject",
            source=codebuild.Source.code_commit(repository=app_project_repo),
            artifacts=codebuild.Artifacts.s3(
                bucket=artifact_bucket,
                include_build_id=True,
                package_zip=True,
                name="artifact.zip",
                path="build_output"
            ),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                compute_type=codebuild.ComputeType.SMALL
            ),
            role=code_build_role
        )

        # Grant the CodeBuild project permissions to write to the S3 bucket
        artifact_bucket.grant_put(app_build_project)

        
        # Create the IAM role for CodePipeline
        pipeline_role = iam.Role(
            self, "CodePipelineServiceRole",
            assumed_by=iam.ServicePrincipal("codepipeline.amazonaws.com"),
            path="/service-role/"
        )

        # Define the policy for the role
        policy = iam.Policy(
            self, "CodePipelinePolicy",
            statements=[
                iam.PolicyStatement(
                    actions=["s3:PutObject", "s3:GetObject", "s3:GetBucketAcl", "s3:GetBucketLocation"],
                    resources=["arn:aws:s3:::artifact-bucket", "arn:aws:s3:::artifact-bucket/*"],
                    effect=iam.Effect.ALLOW
                ),
                iam.PolicyStatement(
                    actions=["codecommit:GetBranch", "codecommit:GetCommit", "codecommit:GetRepository",
                             "codecommit:CancelUploadArchive", "codecommit:UploadArchive"],
                    resources=["*"],
                    effect=iam.Effect.ALLOW
                ),
                iam.PolicyStatement(
                    actions=["codebuild:StartBuild", "codebuild:BatchGetBuilds"],
                    resources=[app_build_project.project_arn],
                    effect=iam.Effect.ALLOW
                )
            ]
        )

        pipeline_role.attach_inline_policy(policy)
        
        # Create the pipeline
        app_code_pipeline = codepipeline.Pipeline(
            self, "AppCodePipeline",
            pipeline_name="AppCodePipeline",
            artifact_bucket=artifact_bucket,
            role=pipeline_role
        )

        # Add Source stage to pipeline
        source_output = codepipeline.Artifact(artifact_name="SourceCode")
        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name="Source",
            repository=app_project_repo,
            output=source_output,
            branch="master"
        )
        app_code_pipeline.add_stage(stage_name="Source", actions=[source_action])

        # Add Build stage to pipeline
        build_action = codepipeline_actions.CodeBuildAction(
            action_name="Build",
            project=app_build_project,
            input=source_output
        )
        app_code_pipeline.add_stage(stage_name="Build", actions=[build_action])