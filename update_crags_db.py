from db import *

log = logging.getLogger('app')

def add_crags():
    current_crags = set(db.session.query(Crag.name).all())
    missing_crags = []
    for crag in crags:
        if not (crag.name,) in current_crags: # query returns names as tuple
            db.session.add(crag)
            missing_crags.append(crag.name)
    db.session.commit()
    log.info("Added Crags: %s" % ','.join(missing_crags))

if __name__ == "__main__":
    add_crags()