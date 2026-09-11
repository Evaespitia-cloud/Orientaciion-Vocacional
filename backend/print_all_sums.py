from app import create_app
from app.models.resultado import PerfilVocacional
from app.models.usuario import Usuario

app = create_app()

with app.app_context():
    print("=== TODAS LAS SUMAS DE PUNTAJES ===")
    perfiles = PerfilVocacional.query.all()
    for p in perfiles:
        if not p.datos_json or 'puntajes_por_area' not in p.datos_json:
            continue
        scores = p.datos_json['puntajes_por_area']
        
        def get_val(area):
            d = scores.get(area, {})
            int_v = d.get('Intereses Vocacionales', d.get('Intereses', 0))
            com_v = d.get('Competencias Vocacionales', d.get('Competencias', 0))
            if int_v == 0 and com_v == 0:
                return d.get('positivas', 0)
            return int_v + com_v
            
        r_v = get_val('Realista')
        i_v = get_val('Investigador')
        a_v = get_val('Artístico')
        s_v = get_val('Social')
        e_v = get_val('Emprendedor')
        c_v = get_val('Convencional')
        
        estudiante = p.aplicacion.usuario if p.aplicacion else None
        est_name = estudiante.nombre_completo if estudiante else 'Desconocido'
        print(f"Estudiante: {est_name} | App ID: {p.aplicacion_id}")
        print(f"  Sums: R={r_v}, I={i_v}, A={a_v}, S={s_v}, E={e_v}, C={c_v}")
        print(f"  Percentages: R={scores.get('Realista',{}).get('normalizado')}%, I={scores.get('Investigador',{}).get('normalizado')}%, C={scores.get('Convencional',{}).get('normalizado')}%")
        print("-" * 50)
