from fastapi import FastAPI, HTTPException, Request, UploadFile, Depends, File, Form
from pydantic import BaseModel
from typing import Dict, List
import uuid
from models.moonshot import llm
from rag import create_ocr_rag_chain, create_rag
from retrievers import imageRetriever
from retrievers.imageRetriever import read_image_from_url, read_image
from retrievers.webRetriever import retriever
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from db.index import SessionLocal
from db.schema import History, OcrHistory, Session, Evaluation, EvaluationData, HistoryListResponse, User
from fastapi.responses import StreamingResponse
from auth.schema import UserResponse, UserCreate, TokenResponse
from firebase_admin import auth
from auth.auth import verify_token, get_password_hash, create_access_token, verify_password, get_current_user
import base64
from graph.index import create_graph, CustomHumanMessage, execute_graph
import os

app = FastAPI()
IMAGE_FOLDER = "./images"

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许的源
    allow_credentials=True,  # 允许发送Cookie
    allow_methods=["*"],  # 允许的方法，如GET、POST等，使用["*"]来允许所有方法
    allow_headers=["*"],  # 允许的请求头，使用["*"]来允许所有请求头
)
session_histories: Dict[str, List[str]] = {}
class InputData(BaseModel):
    input: str
class OcrData(BaseModel):
    image: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
@app.post("/chat/start-session/")
async def start_session(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    db_session = Session(id=session_id)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return {"session_id": session_id}

@app.post("/ocr/upload-invoke/")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    db_user = db.query(User).filter(User.email == user['email']).first()
    image_path = f"./images/{file.filename}"
    contents = await file.read()
    with open(image_path, "wb") as image_file:
        image_file.write(contents)
    file_base64 = base64.b64encode(contents).decode("utf-8")
    questions = imageRetriever.read_question_answer_pair(file_base64)
    responses = [create_ocr_rag_chain(llm)(str(question['question']), str(question['user_answer'])) for question in questions]
    db_ocr_history = OcrHistory(response=str(responses), image_url=f"/images/{file.filename}", wrong_place=responses[0]["response"]["correct"], user_id=db_user.id)
    db.add(db_ocr_history)
    db.commit()
    return {
        "answer": responses,
    }
@app.get("/ocr/history/")
async def get_all_ocr_history(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    db_user = db.query(User).filter(User.email == user['email']).first()
    all_history = db.query(OcrHistory).all()
    user_id = db_user.id

    # 查询数据库，获取与当前用户ID相关的OCR历史记录
    user_ocr_history = db.query(OcrHistory).filter(OcrHistory.user_id == user_id).all()
    if not all_history:
        raise HTTPException(status_code=404, detail="No OCR history found")
    return [
        {
            "id": history.id,
            "response": history.response,
            "image_url": history.image_url,
            "wrong_place": history.wrong_place,
        }
        for history in user_ocr_history
    ]
@app.post("/ocr/invoke")
async def invoke_ocr(data: OcrData, request: Request, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    db_user = db.query(User).filter(User.email == user['email']).first()
    questions = imageRetriever.read_question_answer_pair(read_image_from_url(data.image))
    responses = [create_ocr_rag_chain(llm)(str(question)) for question in questions]
    db_ocr_history = OcrHistory(response=str(responses), image_url=data.image, wrong_place=responses[0]["correct"], user_id=db_user['id'])
    db.add(db_ocr_history)
    db.commit()
    return {
        "answer": responses,
    }
@app.post("/chat/invoke/")
async def invoke_model(data: InputData, request: Request, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    session_id = request.headers.get("Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Invalid or missing Session-ID")
    
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 获取历史记录
    history_records = db.query(History).filter(History.session_id == session_id).all()
    history = [(h.user_input, h.model_response) for h in history_records]
    state = {"messages": [{"author": "system", "content": "start"}]}
    # 调用模型链生成响应
    rag_chain = create_rag(llm)
    graph = create_graph(rag_chain)
    response = execute_graph(graph, data.input + "".join([h[0] for h in history]))
    
    # 保存输入和响应
    db_history = History(session_id=session_id, user_input=data.input, model_response=response)
    db.add(db_history)
    db.commit()
    
    return {
        "answer": response,
        "evaluation_prompt": "Please evaluate the response with a score from 1 to 5, and optionally provide feedback."
    }

@app.post("/chat/evaluate/", response_model=None)
async def evaluate_model(data: EvaluationData, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    session = db.query(Session).filter(Session.id == data.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db_evaluation = Evaluation(session_id=data.session_id, score=data.score, feedback=data.feedback)
    db.add(db_evaluation)
    db.commit()
    
    return {"message": "Evaluation received successfully"}

@app.get("/chat/history/{session_id}", response_model=HistoryListResponse)
async def get_history(session_id: str, db: Session = Depends(get_db),user: dict = Depends(get_current_user)):
    histories = db.query(History).filter(History.session_id == session_id).all()
    if not histories:
        raise HTTPException(status_code=404, detail="No history found for this session")
    return {"histories": histories}

@app.post("/auth/register/", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if the user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create a new user
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"detail": 'successfully registered'}


@app.post("/auth/login/", response_model=TokenResponse)
def login(user: UserCreate, db: Session = Depends(get_db)):
    # Check if the user exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user is None or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate JWT token
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}

# 提交个人信息接口
@app.post("/submit-info/")
async def submit_info(
    nickname: str = Form(None),
    avatar: UploadFile = File(None),
    db: Session = Depends(get_db),
    userToken: Dict = Depends(get_current_user)
):
    if not userToken:
        raise HTTPException(status_code=401, detail="token not found")
    user = db.query(User).filter(User.email == userToken["email"]).first()
    image_path = f"./images/{avatar.filename}"
    # 更新昵称和头像
    if nickname:
        user.nickname = nickname
    if avatar:
        # 处理上传的头像文件
        avatar_data = await avatar.read()
        with open(image_path, "wb") as f:
            f.write(avatar_data)
        image_url = f"/images/{avatar.filename}"
        user.avatar_data = image_url

    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "nickname": user.nickname, "avatar": image_url}

# 获取个人信息接口
@app.get("/get-info")
async def get_info(db: Session = Depends(get_db), userToken: Dict = Depends(get_current_user)):
    incorrect_count = db.query(OcrHistory).filter(OcrHistory.wrong_place == False).count()
    user = db.query(User).filter(User.email == userToken["email"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
        "incorrect_num": incorrect_count,
        "avatar_data": user.avatar_data
    }
    
@app.get("/images/{filename}")
async def get_image(filename: str):
    try:
        # 构建图片的相对路径
        image_path = os.path.join(IMAGE_FOLDER, filename)
        # 检查文件是否存在
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image not found")
        # 返回图片的StreamingResponse
        return StreamingResponse(open(image_path, "rb"), media_type="image/png")
    except IOError:
        raise HTTPException(status_code=500, detail="Server error")