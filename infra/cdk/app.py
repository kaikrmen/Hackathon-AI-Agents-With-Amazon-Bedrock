import aws_cdk as cdk
from stacks.core_stack import CoreStack

app = cdk.App()
CoreStack(app, "KaiKashiCoreStack", env=cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-west-2",
))
app.synth()
