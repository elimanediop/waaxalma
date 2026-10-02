from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from mutagen import File as MutagenFile
from mutagen import MutagenError
from starlette import status

from app.exceptions.error_codes import ErrorCode
from app.validation.validation_error import AudioValidationError


@dataclass(frozen=True, slots=True)
class ValidatedAudio:
    path: Path
    extension: str
    mime_type: str | None
    size_bytes: int
    duration_seconds: float


class AudioValidator:
    """
    Validates and stores an uploaded audio file.

    Validation includes:

    - filename extension;
    - declared MIME type;
    - maximum file size;
    - non-empty content;
    - readable audio metadata;
    - consistency between extension and detected content type;
    - maximum audio duration.
    """

    GENERIC_MIME_TYPES = {
        "",
        "application/octet-stream",
        "binary/octet-stream",
    }

    SUPPORTED_MIME_TYPES: dict[str, set[str]] = {
        "wav": {
            "audio/wav",
            "audio/wave",
            "audio/x-wav",
            "audio/vnd.wave",
        },
        "mp3": {
            "audio/mpeg",
            "audio/mp3",
            "audio/x-mp3",
        },
        "ogg": {
            "audio/ogg",
            "application/ogg",
        },
        "m4a": {
            "audio/mp4",
            "audio/m4a",
            "audio/x-m4a",
        },
        "flac": {
            "audio/flac",
            "audio/x-flac",
        },
    }

    def __init__(
        self,
        upload_dir: str | Path,
        max_size_bytes: int = 20 * 1024 * 1024,
        max_duration_seconds: float = 120.0,
        chunk_size_bytes: int = 1024 * 1024,
    ) -> None:
        if max_size_bytes <= 0:
            raise ValueError("max_size_bytes must be greater than zero")

        if max_duration_seconds <= 0:
            raise ValueError(
                "max_duration_seconds must be greater than zero"
            )

        if chunk_size_bytes <= 0:
            raise ValueError("chunk_size_bytes must be greater than zero")

        self.upload_dir = Path(upload_dir)
        self.max_size_bytes = max_size_bytes
        self.max_duration_seconds = max_duration_seconds
        self.chunk_size_bytes = chunk_size_bytes

        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def validate_and_save(
        self,
        file: UploadFile,
        request_id: str,
    ) -> ValidatedAudio:
        extension = self._extract_extension(file.filename)

        declared_mime_type = self._normalize_mime_type(
            file.content_type
        )

        self._validate_declared_mime_type(
            extension=extension,
            mime_type=declared_mime_type,
        )

        destination = self.upload_dir / f"{request_id}.{extension}"

        try:
            size_bytes = await self._save_with_size_limit(
                file=file,
                destination=destination,
            )

            duration_seconds, detected_mime_type = (
                self._inspect_audio_file(
                    path=destination,
                    extension=extension,
                )
            )

            return ValidatedAudio(
                path=destination,
                extension=extension,
                mime_type=detected_mime_type or declared_mime_type or None,
                size_bytes=size_bytes,
                duration_seconds=duration_seconds,
            )

        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def _extract_extension(
        self,
        filename: str | None,
    ) -> str:
        if not filename:
            raise AudioValidationError(
                code=ErrorCode.UNSUPPORTED_AUDIO_FORMAT,
                message="The uploaded audio file must have a filename.",
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        extension = Path(filename).suffix.lower().lstrip(".")

        if not extension:
            raise AudioValidationError(
                code=ErrorCode.UNSUPPORTED_AUDIO_FORMAT,
                message="The uploaded audio file has no extension.",
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        if extension not in self.SUPPORTED_MIME_TYPES:
            raise AudioValidationError(
                code=ErrorCode.UNSUPPORTED_AUDIO_FORMAT,
                message=f"Audio format '.{extension}' is not supported.",
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                details={
                    "extension": extension,
                    "supported_extensions": sorted(
                        self.SUPPORTED_MIME_TYPES.keys()
                    ),
                },
            )

        return extension

    def _validate_declared_mime_type(
        self,
        extension: str,
        mime_type: str,
    ) -> None:
        # Some clients send application/octet-stream.
        # In that case, the real file content is validated after upload.
        if mime_type in self.GENERIC_MIME_TYPES:
            return

        allowed_mime_types = self.SUPPORTED_MIME_TYPES[extension]

        if mime_type not in allowed_mime_types:
            raise AudioValidationError(
                code=ErrorCode.UNSUPPORTED_AUDIO_MIME_TYPE,
                message=(
                    f"MIME type '{mime_type}' is not valid "
                    f"for '.{extension}' audio files."
                ),
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                details={
                    "extension": extension,
                    "received_mime_type": mime_type,
                    "allowed_mime_types": sorted(allowed_mime_types),
                },
            )

    async def _save_with_size_limit(
        self,
        file: UploadFile,
        destination: Path,
    ) -> int:
        total_size = 0

        await file.seek(0)

        with destination.open("wb") as buffer:
            while True:
                chunk = await file.read(self.chunk_size_bytes)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > self.max_size_bytes:
                    raise AudioValidationError(
                        code=ErrorCode.AUDIO_TOO_LARGE,
                        message="The uploaded audio file is too large.",
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        details={
                            "received_size_bytes": total_size,
                            "maximum_size_bytes": self.max_size_bytes,
                        },
                    )

                buffer.write(chunk)

        if total_size == 0:
            raise AudioValidationError(
                code=ErrorCode.EMPTY_AUDIO,
                message="The uploaded audio file is empty.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return total_size

    def _inspect_audio_file(
        self,
        path: Path,
        extension: str,
    ) -> tuple[float, str | None]:
        try:
            audio = MutagenFile(path)

        except (MutagenError, OSError, ValueError) as exc:
            raise AudioValidationError(
                code=ErrorCode.CORRUPTED_AUDIO,
                message=(
                    "The uploaded file could not be decoded "
                    "as a valid audio file."
                ),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            ) from exc

        if audio is None or getattr(audio, "info", None) is None:
            raise AudioValidationError(
                code=ErrorCode.CORRUPTED_AUDIO,
                message=(
                    "The uploaded file does not contain "
                    "readable audio data."
                ),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        duration = float(
            getattr(audio.info, "length", 0.0) or 0.0
        )

        if not math.isfinite(duration) or duration <= 0:
            raise AudioValidationError(
                code=ErrorCode.CORRUPTED_AUDIO,
                message=(
                    "The audio duration could not be determined "
                    "or is invalid."
                ),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if duration > self.max_duration_seconds:
            raise AudioValidationError(
                code=ErrorCode.AUDIO_TOO_LONG,
                message="The uploaded audio file is too long.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                details={
                    "duration_seconds": round(duration, 3),
                    "maximum_duration_seconds": (
                        self.max_duration_seconds
                    ),
                },
            )

        detected_mime_types = {
            self._normalize_mime_type(item)
            for item in getattr(audio, "mime", []) or []
        }

        allowed_mime_types = self.SUPPORTED_MIME_TYPES[extension]

        if (
            detected_mime_types
            and detected_mime_types.isdisjoint(allowed_mime_types)
        ):
            raise AudioValidationError(
                code=ErrorCode.AUDIO_TYPE_MISMATCH,
                message=(
                    "The file extension does not match "
                    "the detected audio content."
                ),
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                details={
                    "extension": extension,
                    "detected_mime_types": sorted(
                        detected_mime_types
                    ),
                    "expected_mime_types": sorted(
                        allowed_mime_types
                    ),
                },
            )

        detected_mime_type = next(
            iter(sorted(detected_mime_types)),
            None,
        )

        return duration, detected_mime_type

    @staticmethod
    def _normalize_mime_type(
        mime_type: str | None,
    ) -> str:
        if not mime_type:
            return ""

        return mime_type.split(";", maxsplit=1)[0].strip().lower()