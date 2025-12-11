import sqlite3
import os

# Caminho para o banco de dados
db_path = os.path.join(os.path.dirname(__file__), 'funcionalidades', 'db.sqlite3')

def check_database():
    print(f"🔌 Conectando ao banco de dados em: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Verificar Usuários
        print("\n--- 👤 Usuários Cadastrados ---")
        cursor.execute("SELECT id, username, email, is_active FROM auth_user")
        users = cursor.fetchall()
        
        if not users:
            print("⚠️ Nenhum usuário encontrado.")
        else:
            print(f"{'ID':<5} {'Username':<15} {'Email':<30} {'Ativo?'}")
            print("-" * 60)
            for user in users:
                print(f"{user[0]:<5} {user[1]:<15} {user[2]:<30} {bool(user[3])}")

        # 2. Verificar Favoritos
        print("\n--- ⭐ Artigos Salvos (Favoritos) ---")
        try:
            cursor.execute("""
                SELECT f.id, u.username, f.title, f.year 
                FROM favorites_favorite f
                JOIN auth_user u ON f.user_id = u.id
            """)
            favorites = cursor.fetchall()
            
            if not favorites:
                print("⚠️ Nenhum favorito salvo encontrado.")
            else:
                print(f"{'ID':<5} {'Usuário':<15} {'Ano':<6} {'Título'}")
                print("-" * 60)
                for fav in favorites:
                    print(f"{fav[0]:<5} {fav[1]:<15} {fav[3] or 'N/A':<6} {fav[2][:40]}...")
        except sqlite3.OperationalError:
            print("⚠️ A tabela de favoritos ainda não existe ou está vazia.")

        conn.close()
        print("\n✅ Verificação concluída com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro ao ler o banco de dados: {e}")

if __name__ == "__main__":
    check_database()
