# app/components/voice_qa/routers/voice_router.py

from fastapi import APIRouter, UploadFile, File, Form

from app.components.voice_qa.whisper_service import VoiceService, VoiceQAService
from app.services.audio_storage import upload_audio_to_firebase
from app.services.chat_service import save_chat_message
from uuid import UUID

router = APIRouter()

# @router.get("/health")
# async def health_check():
#     """
#     Health check endpoint for Voice component.
#     """
#     return {"status": "Voice component is healthy."}


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):

    temp_path = "temp.wav"
    with open(temp_path, "wb") as f:
        f.write(await audio.read())

    raw_text = VoiceService.transcribe_audio(temp_path)
    normalized, standard = VoiceService.standardize_southern_sinhala(raw_text)

    return {
        "raw": raw_text,
        "normalized": normalized,
        "standard": standard,
    }


# The heavier pipeline helpers live in `VoiceQAService` (in whisper_service.py).


@router.post("/qa")
async def qa_from_voice(audio: UploadFile = File(...), session_id: str = Form(...), top_k: int = 3):
    """
    Full voice → QA pipeline.

    Steps:
      - save incoming audio
      - transcribe (whisper)
      - generate embedding for the question
      - retrieve top-k chunks from pgvector
      - build prompt and call LLM
      - return question, retrieved chunks, and answer
    """

    temp_path = "temp.wav"
    with open(temp_path, "wb") as f:
        f.write(await audio.read())

    # Note: this endpoint intentionally keeps the upload/transcription + storage
    # flow explicit so we can persist the audio URL and chat history.

    # 1) Upload to Firebase Storage
    audio_url = None
    try:
        audio_url = upload_audio_to_firebase(temp_path, session_id)
    except Exception as e:
        print(f"[voice_router] upload to firebase failed: {e}")

    # 2) Transcribe and standardize
    raw_text = VoiceService.transcribe_audio(temp_path)
    normalized, standard = VoiceService.standardize_southern_sinhala(raw_text)
    question_text = standard or normalized or raw_text

    # 3) Save user message to chat_messages
    try:
        save_chat_message(session_id=UUID(session_id), sender="user", message=question_text, tokens_used=0, audio_url=audio_url)
    except Exception as e:
        print(f"[voice_router] failed to save user chat message: {e}")

    # 4) Run RAG + LLM
    # use helpers from VoiceQAService but avoid re-transcribing (we already have text)
    question_embedding = VoiceQAService.generate_text_embedding(question_text)
    top_chunks = VoiceQAService.find_similar_chunks(question_embedding, top_k=top_k)
    prompt = VoiceQAService.build_prompt(question_text, top_chunks)
    answer = VoiceQAService.llm_generate(prompt)

    # 5) Save assistant message
    tokens_used = 0
    # TODO: extract actual token usage from LLM response if available
    try:
        save_chat_message(session_id=UUID(session_id), sender="assistant", message=answer, tokens_used=tokens_used)
    except Exception as e:
        print(f"[voice_router] failed to save assistant chat message: {e}")

    # Step 6 — return
    return {
        "question": question_text,
        "retrieved_chunks": top_chunks,
        "answer": answer,
    }