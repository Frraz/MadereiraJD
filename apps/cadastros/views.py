from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Cliente, TipoMadeira, Motorista
from .forms import ClienteForm, TipoMadeiraForm, MotoristaForm

from django.contrib.auth.models import User
from django import forms
from django.db.models import Q

# ========== CLIENTES ==========

class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = 'cadastros/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        busca = self.request.GET.get('q')
        if busca:
            queryset = queryset.filter(nome__icontains=busca)
        filtro_saldo = self.request.GET.get('saldo')
        if filtro_saldo == 'negativos':
            queryset = [c for c in queryset if c.saldo_atual < 0]
        elif filtro_saldo == 'positivos':
            queryset = [c for c in queryset if c.saldo_atual > 0]
        elif filtro_saldo == 'zerados':
            queryset = [c for c in queryset if c.saldo_atual == 0]
        ordenar = self.request.GET.get('ordenar', 'nome')
        if ordenar == 'saldo':
            queryset = sorted(queryset, key=lambda c: c.saldo_atual)
        elif ordenar == 'saldo_desc':
            queryset = sorted(queryset, key=lambda c: c.saldo_atual, reverse=True)
        else:
            queryset = sorted(queryset, key=lambda c: c.nome.lower())
        return queryset

class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cadastros/cliente_form.html'
    success_url = reverse_lazy('cadastros:cliente_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente cadastrado com sucesso!')
        return super().form_valid(form)

class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'cadastros/cliente_form.html'
    success_url = reverse_lazy('cadastros:cliente_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente atualizado com sucesso!')
        return super().form_valid(form)

class ClienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Cliente
    template_name = 'cadastros/cliente_confirm_delete.html'
    success_url = reverse_lazy('cadastros:cliente_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Cliente excluído com sucesso!')
        return super().delete(request, *args, **kwargs)

# ========== TIPOS DE MADEIRA ==========

class TipoMadeiraListView(LoginRequiredMixin, ListView):
    model = TipoMadeira
    template_name = 'cadastros/tipo_madeira_list.html'
    context_object_name = 'tipos_madeira'
    paginate_by = 30

    def get_queryset(self):
        queryset = super().get_queryset()
        busca = self.request.GET.get('q')
        if busca:
            queryset = queryset.filter(nome__icontains=busca)
        return queryset

class TipoMadeiraCreateView(LoginRequiredMixin, CreateView):
    model = TipoMadeira
    form_class = TipoMadeiraForm
    template_name = 'cadastros/tipo_madeira_form.html'
    success_url = reverse_lazy('cadastros:tipo_madeira_list')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de madeira cadastrado com sucesso!')
        return super().form_valid(form)

class TipoMadeiraUpdateView(LoginRequiredMixin, UpdateView):
    model = TipoMadeira
    form_class = TipoMadeiraForm
    template_name = 'cadastros/tipo_madeira_form.html'
    success_url = reverse_lazy('cadastros:tipo_madeira_list')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de madeira atualizado com sucesso!')
        return super().form_valid(form)

class TipoMadeiraDeleteView(LoginRequiredMixin, DeleteView):
    model = TipoMadeira
    template_name = 'cadastros/tipo_madeira_confirm_delete.html'
    success_url = reverse_lazy('cadastros:tipo_madeira_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Tipo de madeira excluída com sucesso!')
        return super().delete(request, *args, **kwargs)

# ========== MOTORISTAS ==========

class MotoristaListView(LoginRequiredMixin, ListView):
    model = Motorista
    template_name = 'cadastros/motorista_list.html'
    context_object_name = 'motoristas'
    paginate_by = 20

class MotoristaCreateView(LoginRequiredMixin, CreateView):
    model = Motorista
    form_class = MotoristaForm
    template_name = 'cadastros/motorista_form.html'
    success_url = reverse_lazy('cadastros:motorista_list')

    def form_valid(self, form):
        messages.success(self.request, 'Motorista cadastrado com sucesso!')
        return super().form_valid(form)

class MotoristaUpdateView(LoginRequiredMixin, UpdateView):
    model = Motorista
    form_class = MotoristaForm
    template_name = 'cadastros/motorista_form.html'
    success_url = reverse_lazy('cadastros:motorista_list')

    def form_valid(self, form):
        messages.success(self.request, 'Motorista atualizado com sucesso!')
        return super().form_valid(form)

class MotoristaDeleteView(LoginRequiredMixin, DeleteView):
    model = Motorista
    template_name = 'cadastros/motorista_confirm_delete.html'
    success_url = reverse_lazy('cadastros:motorista_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Motorista excluído com sucesso!')
        return super().delete(request, *args, **kwargs)

# ========== USUÁRIOS / OPERADORES (apenas staff e superuser) ==========

class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff  # staff e superuser podem acessar

# Form para operadores comuns (não edita is_superuser)
class UserStaffForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff']

# Form para superusers (pode editar tudo)
class UserSuperForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser']

class UsuarioListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = User
    template_name = 'cadastros/usuario_list.html'
    context_object_name = 'usuarios'
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.order_by('username')
        if not self.request.user.is_superuser:
            qs = qs.filter(is_superuser=False)
        busca = self.request.GET.get('q')
        if busca:
            qs = qs.filter(
                Q(username__icontains=busca)
                | Q(first_name__icontains=busca)
                | Q(last_name__icontains=busca)
                | Q(email__icontains=busca)
            )
        return qs

class UsuarioCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = User
    template_name = 'cadastros/usuario_form.html'
    success_url = reverse_lazy('cadastros:usuario_list')

    def get_form_class(self):
        # Só superuser pode criar outros superusers
        if self.request.user.is_superuser:
            return UserSuperForm
        return UserStaffForm

    def form_valid(self, form):
        form.instance.set_password('123456')
        messages.success(self.request, 'Usuário cadastrado com sucesso! (Senha padrão: 123456)')
        return super().form_valid(form)

class UsuarioUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = User
    template_name = 'cadastros/usuario_form.html'
    success_url = reverse_lazy('cadastros:usuario_list')

    def get_form_class(self):
        if self.request.user.is_superuser:
            return UserSuperForm
        return UserStaffForm

    def form_valid(self, form):
        messages.success(self.request, 'Usuário atualizado com sucesso!')
        return super().form_valid(form)