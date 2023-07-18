{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeSpotPriceHistory",
                "ec2:GetInstanceTypesFromInstanceRequirements",
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceTypes",
                "pricing:GetProducts",
                "account:ListRegions"
            ],
            "Resource": "*"
        }
    ]
}