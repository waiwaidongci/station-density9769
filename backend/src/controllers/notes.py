from ..services import notes
class NotesController:
    list=staticmethod(notes.list_notes)
    create=staticmethod(notes.create_note)
    approve=staticmethod(notes.approve_note)
