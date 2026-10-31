from pydantic import BaseModel, Field

class Defect(BaseModel):
    type: str = Field(description='Defect category')
    description: str = Field(description='Concise visual observation')
    box: list[int] = Field(description='[ymin,xmin,ymax,xmax] on 0-1000 scale')

class InspectionPrediction(BaseModel):
    status: str = Field(description='PASS or FAIL')
    defects: list[Defect] = Field(default_factory=list)
    summary: str = ''
