from supabase import Client, create_client
from app.core.config import settings

# Initialize Supabase client with secret key (service role) to bypass RLS for server-side operations
supabase_client: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SECRET_KEY,
)
