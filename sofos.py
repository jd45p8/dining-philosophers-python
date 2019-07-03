from mpi4py import MPI
from random import randint
import time
import sys
import numpy as np

if len(sys.argv) > 1:
    comm = MPI.COMM_WORLD
    size = comm.Get_size()
    rank = comm.Get_rank()
    amigables = (size - 3)
    if amigables < 0:
        amigables = 0
    ambiciosos = (size - 1) - amigables

    forkSize = MPI.DOUBLE.Get_size()
    nforks = size-1
    if rank == 0:
        nbytes = nforks * forkSize
    else:
        nbytes = 0
    win = MPI.Win.Allocate_shared(nbytes, forkSize, comm=comm)

    # Crea un array de numpy que apunte a el espacio de memoria reservado
    buf, forkSize = win.Shared_query(0)
    assert forkSize == MPI.DOUBLE.Get_size()
    forks = np.ndarray(buffer=buf, dtype='d', shape=(nforks,))

    # Crea un array compartido par alos estados de los procesos
    status_size = forkSize
    win_procesess_status = MPI.Win.Allocate_shared(nbytes, status_size, comm=comm)
    buf2, status_size = win_procesess_status.Shared_query(0)
    assert status_size == MPI.DOUBLE.Get_size()
    processes_status = np.ndarray(buffer=buf2, dtype='d', shape=(nforks))

    if rank is 0:
        tipo_filosofo = np.zeros(nforks + 1)
        # Evita que se escojan el mismo filósofo dos veces como ambicioso
        anterior = 0
        nuevo = anterior
        for i in range(0, ambiciosos):
            while nuevo is anterior:
                nuevo = randint(1, size-1)
            tipo_filosofo[nuevo] = True
            anterior = nuevo
        tipo_filosofos = tipo_filosofo
    else:
        tipo_filosofo = None

    tipo_filosofo = comm.scatter(tipo_filosofo, root=0)

    if rank is 0:
        while size > 1:
            toprint = [""]*7
            win.Lock(0, lock_type=MPI.LOCK_EXCLUSIVE)
            for i in range(0,nforks):
                toprint[0] += "|==========================="
                tipo = "Amigable " if tipo_filosofos[i+1] == 0 else "Ambicioso"
                toprint[1] += "|   Filósofo " + str(i+1) + " (" + tipo + ")  "
                toprint[2] += "|---------------------------"
                left_fork = "X" if forks[i] == i+1 else "-"
                if nforks > 1:
                    if i+1 == nforks:
                        right_fork = "X" if forks[0] == i+1 else "-"
                    else:
                        right_fork = "X" if forks[i+1] == i+1 else "-"
                else:
                    right_fork = "-"
                toprint[3] += "|      " + left_fork + "      |      " + right_fork + "      "
                toprint[4] += "|---------------------------"
                available_fork = "X" if forks[i] == 0 else "-"
                toprint[5] += "|             " + available_fork + "             "
                toprint[6] += "|==========================="
            win.Unlock(0)
            
            for i in range(0,7):
                print(toprint[i] + "|")
            print("")
            sys.stdout.flush()

            time.sleep(1)
            terminado = True
            for i in range(0,nforks):
                if processes_status[i] == 0:
                    terminado = False
                    break
            if terminado:
                break
    else:
        K = int(sys.argv[1])
        for k in range(1, K+1):
            # Pensando
            time.sleep(randint(7, 10))

            # Bloquear el acceso al recurso compartido
            win.Lock(0, lock_type=MPI.LOCK_EXCLUSIVE)

            if tipo_filosofo == 1:
                # Tomar el tenedor izquierdo
                while True:
                    if forks[rank-1] == 0:
                        forks[rank-1] = rank
                        # Toma el tenedor derecho
                        while True:
                            if rank == nforks:
                                if forks[0] == 0:
                                    forks[0] = rank
                                    break
                            else:
                                if forks[rank] == 0:
                                    forks[rank] = rank
                                    break
                            win.Unlock(0)
                            win.Lock(0, lock_type=MPI.LOCK_EXCLUSIVE)
                        break
                    win.Unlock(0)
                    win.Lock(0, lock_type=MPI.LOCK_EXCLUSIVE)
            else:
                while True:
                    # Tomar el tenedor izquierdo
                    if forks[rank-1] == 0:
                        forks[rank-1] = rank
                        # Toma el tenedor derecho
                        for i in range(0, 2):
                            if rank == nforks:
                                if forks[0] == 0:
                                    forks[0] = rank
                                    break
                            else:
                                if forks[rank] == 0:
                                    forks[rank] = rank
                                    break
                            if i < 1:
                                win.Unlock(0)
                                time.sleep(randint(5, 15))
                                win.Lock(0, lock_type=MPI.LOCK_EXCLUSIVE)
                        if i is 2:
                            forks[rank-1] = 0
                            win.Unlock(0)
                        else:
                            break
                    win.Unlock(0)
                    win.Lock(0, lock_type=MPI.LOCK_EXCLUSIVE)
            win.Unlock(0)
            # Comiendo
            time.sleep(randint(2, 5))

            # Liberar los tenedores
            win.Lock(0)
            forks[rank-1] = 0
            if rank == nforks:
                forks[0] = 0
            else:
                forks[rank] = 0
            win.Unlock(0)

            # Pensando (NO ESTOY SEGURO DE TENER QUE PENSAR DESPUÉS DE COMER)
            time.sleep(randint(7, 10))
        win_procesess_status.Lock(0)
        processes_status[rank-1] = 1
        win_procesess_status.Unlock(0)
else:
    print("Se esperaba 1 argumento.")
