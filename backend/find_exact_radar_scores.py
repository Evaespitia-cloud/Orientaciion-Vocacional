from app import create_app
from app.models.resultado import PerfilVocacional
from app.models.usuario import Usuario

app = create_app()

with app.app_context():
    print("=== BUSCANDO COINCIDENCIA DE PUNTAJES DEL RADAR ===")
    perfiles = PerfilVocacional.query.all()
    for p in perfiles:
        if not p.datos_json or 'puntajes_por_area' not in p.datos_json:
            continue
        scores = p.datos_json['puntajes_por_area']
        
        # Obtener los valores bruto/positivas para cada area (sumando Intereses y Competencias)
        def get_val(area):
            d = scores.get(area, {})
            int_v = d.get('Intereses Vocacionales', d.get('Intereses', 0))
            com_v = d.get('Competencias Vocacionales', d.get('Competencias', 0))
            # Si no hay esas llaves, probar con 'positivas'
            if int_v == 0 and com_v == 0:
                return d.get('positivas', 0)
            return int_v + com_v
            
        r_v = get_val('Realista')
        i_v = get_val('Investigador')
        a_v = get_val('Artístico')
        s_v = get_val('Social')
        e_v = get_val('Emprendedor')
        c_v = get_val('Convencional')
        
        # Si coincide con R:4, I:3, C:3, A:2, S:1, E:1 exactly
        if r_v == 4 and i_v == 3 and a_v == 2 and s_v == 1 and e_v == 1 and c_v == 3:
            estudiante = p.aplicacion.usuario if p.aplicacion else None
            est_name = estudiante.nombre_completo if estudiante else 'Desconocido'
            print(f"EXACT MATCH found! Estudiante: {est_name} | App ID: {p.aplicacion_id}")
            print(f"  Scores: R={r_v}, I={i_v}, A={a_v}, S={s_v}, E={e_v}, C={c_v}")
            print("  Datos JSON completos:", p.datos_json)
            found = True
            print("-" * 50)
