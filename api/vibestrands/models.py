import boto3

class BedrockModel:
    def __init__(self, model_id: str, region: str = None, aws_access_key_id: str = None, aws_secret_access_key: str = None, endpoint_url: str = None):
        self.model_id = model_id
        
        kwargs = {}
        if region: kwargs["region_name"] = region
        if aws_access_key_id: kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key: kwargs["aws_secret_access_key"] = aws_secret_access_key
        if endpoint_url: kwargs["endpoint_url"] = endpoint_url
        
        self.client = boto3.client("bedrock-runtime", **kwargs)

    def converse(self, system: list, messages: list) -> str:
        res = self.client.converse(
            modelId=self.model_id,
            system=system,
            messages=messages,
            inferenceConfig={"temperature": 0.8, "topP": 0.9}
        )
        return res["output"]["message"]["content"][0]["text"]
