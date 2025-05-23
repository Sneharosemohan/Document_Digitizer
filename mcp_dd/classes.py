class EmailCredentials(BaseModel):
    email_id: str
    password: str

class AttachmentIDs(BaseModel):
    attachment_ids: List[str]