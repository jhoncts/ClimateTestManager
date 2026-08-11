from pathlib import Path

path = Path("src/climatetest_manager/services/auth.py")
text = path.read_text(encoding="utf-8")

old_import = "from climatetest_manager.repositories.users import UserRepository\n"
new_import = (
    old_import
    + "from climatetest_manager.services.profile_photos import (\n"
    + "    ProfilePhotoError,\n"
    + "    optimize_profile_photo,\n"
    + ")\n"
)
if "from climatetest_manager.services.profile_photos import" not in text:
    if old_import not in text:
        raise SystemExit("Import anchor not found")
    text = text.replace(old_import, new_import, 1)

start = text.index("    def set_profile_photo(\n")
end = text.index("    @staticmethod\n    def _require_admin", start)
replacement = '''    def set_profile_photo(
        self,
        user: UserSummary,
        image_bytes: bytes | None,
    ) -> UserSummary:
        """Salva um avatar otimizado no banco para manter a LAN rápida e o backup completo."""

        encoded: str | None = None
        if image_bytes is not None:
            try:
                optimized = optimize_profile_photo(image_bytes)
            except ProfilePhotoError as error:
                raise AuthenticationError(str(error)) from error
            encoded = base64.b64encode(optimized).decode("ascii")
        self._repository.mutate(
            user.id,
            lambda target: setattr(target, "profile_photo_b64", encoded),
        )
        refreshed = self._repository.get(user.id)
        if refreshed is None:
            raise AuthenticationError("Usuário não encontrado após atualizar a foto.")
        self._repository.add_security_event(
            actor_user_id=user.id,
            actor_label=user.actor_label,
            action="Foto de perfil alterada" if encoded else "Foto de perfil removida",
            target_user_id=user.id,
        )
        return _summary(refreshed)

'''
text = text[:start] + replacement + text[end:]
path.write_text(text, encoding="utf-8")
